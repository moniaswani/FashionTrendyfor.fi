// POST /billing/subscription-action — authenticated (same CognitoAuthorizer
// as toggleLike). Body: { action: "cancel" | "resume" | "pause" | "unpause" }.
//
// Lets a signed-in user manage their own subscription in-app instead of
// being dropped straight into Stripe's hosted Billing Portal for every
// action — that's still available separately (createPortalSession) for
// payment-method updates and invoice history, which really do belong to
// Stripe's own UI.
//
//   cancel  -> cancel_at_period_end=true  (access continues until the
//              period they already paid for ends, same "at period end"
//              behavior the Billing Portal config already used)
//   resume  -> cancel_at_period_end=false (undo a pending cancellation)
//   pause   -> pause_collection[behavior]=mark_uncollectible (stops billing;
//              Stripe does NOT change subscription.status for this, so
//              access continues during a pause — same as a billing hold,
//              not a hard lockout)
//   unpause -> pause_collection="" (Stripe's documented way to unset an
//              object-valued param via the form-encoded API)
//
// The Stripe secret key is never a Lambda env var — fetched from SSM
// Parameter Store (SecureString) at runtime and cached in memory, same
// pattern as every other billing Lambda in this repo.

import { SSMClient, GetParameterCommand } from "@aws-sdk/client-ssm";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, GetCommand } from "@aws-sdk/lib-dynamodb";

const REGION = "eu-west-2";
const STRIPE_SECRET_PARAM = "/runway-gallery/stripe-secret-key";
const SUBSCRIPTIONS_TABLE = "RunwaySubscriptions";
const VALID_ACTIONS = new Set(["cancel", "resume", "pause", "unpause"]);

const ssm = new SSMClient({ region: REGION });
const db = DynamoDBDocumentClient.from(new DynamoDBClient({ region: REGION }));
let cachedSecretKey = null;

async function getStripeSecretKey() {
  if (cachedSecretKey) return cachedSecretKey;
  const resp = await ssm.send(new GetParameterCommand({ Name: STRIPE_SECRET_PARAM, WithDecryption: true }));
  cachedSecretKey = resp.Parameter.Value;
  return cachedSecretKey;
}

function paramsForAction(action) {
  const params = new URLSearchParams();
  if (action === "cancel") params.set("cancel_at_period_end", "true");
  else if (action === "resume") params.set("cancel_at_period_end", "false");
  else if (action === "pause") params.set("pause_collection[behavior]", "mark_uncollectible");
  else if (action === "unpause") params.set("pause_collection", "");
  return params;
}

export const handler = async (event) => {
  try {
    const userId = event.requestContext?.authorizer?.jwt?.claims?.sub;
    if (!userId) return response(401, { error: "Unauthorized" });

    let action;
    try {
      action = JSON.parse(event.body || "{}").action;
    } catch {
      return response(400, { error: "Invalid JSON body" });
    }
    if (!VALID_ACTIONS.has(action)) {
      return response(400, { error: `action must be one of: ${[...VALID_ACTIONS].join(", ")}` });
    }

    const row = await db.send(new GetCommand({ TableName: SUBSCRIPTIONS_TABLE, Key: { user_id: userId } }));
    const subscriptionId = row.Item?.stripe_subscription_id;
    if (!subscriptionId) return response(404, { error: "No subscription found" });

    const secretKey = await getStripeSecretKey();
    const stripeResp = await fetch(`https://api.stripe.com/v1/subscriptions/${subscriptionId}`, {
      method: "POST",
      headers: {
        Authorization: `Basic ${Buffer.from(`${secretKey}:`).toString("base64")}`,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: paramsForAction(action).toString(),
    });

    const subscription = await stripeResp.json();
    if (!stripeResp.ok) {
      console.error("Stripe error updating subscription:", subscription);
      return response(502, { error: subscription.error?.message || "Stripe request failed" });
    }

    // Return the fresh values directly rather than making the frontend wait
    // for the async webhook to catch up (customer.subscription.updated will
    // still fire and reconcile RunwaySubscriptions the normal way).
    return response(200, {
      status: subscription.status,
      cancel_at_period_end: subscription.cancel_at_period_end,
      paused: !!subscription.pause_collection,
      current_period_end: subscription.current_period_end ?? null,
    });
  } catch (err) {
    console.error("manageSubscription error:", err);
    return response(500, { error: err.message || "Internal error" });
  }
};

function response(statusCode, body) {
  return {
    statusCode,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Headers": "Authorization,Content-Type",
    },
    body: JSON.stringify(body),
  };
}
