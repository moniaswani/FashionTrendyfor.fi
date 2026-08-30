// POST /billing/portal-session — authenticated. Creates a Stripe Billing
// Portal session (hosted, same pattern as Checkout) for the caller's own
// Stripe customer and returns the redirect URL. The portal itself handles
// cancellation, payment method updates, and invoice history — no custom
// cancel UI built here on purpose, same reasoning as using hosted Checkout
// instead of a custom payment form.
//
// Portal config (bpc_1U8x5eRqfP1gbqgE5UB6RFFE, set as this account's
// default): subscription_cancel enabled, mode "at_period_end" (a
// cancellation lets the current paid/trial period run out rather than
// cutting access immediately), payment_method_update + invoice_history
// enabled.

import { SSMClient, GetParameterCommand } from "@aws-sdk/client-ssm";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, GetCommand } from "@aws-sdk/lib-dynamodb";

const REGION = "eu-west-2";
const STRIPE_SECRET_PARAM = "/runway-gallery/stripe-secret-key";
const SUBSCRIPTIONS_TABLE = "RunwaySubscriptions";
const APP_ORIGIN = process.env.APP_ORIGIN || "http://localhost:5173";

const ssm = new SSMClient({ region: REGION });
const db = DynamoDBDocumentClient.from(new DynamoDBClient({ region: REGION }));
let cachedSecretKey = null;

async function getStripeSecretKey() {
  if (cachedSecretKey) return cachedSecretKey;
  const resp = await ssm.send(new GetParameterCommand({ Name: STRIPE_SECRET_PARAM, WithDecryption: true }));
  cachedSecretKey = resp.Parameter.Value;
  return cachedSecretKey;
}

export const handler = async (event) => {
  try {
    const userId = event.requestContext?.authorizer?.jwt?.claims?.sub;
    if (!userId) return response(401, { error: "Unauthorized" });

    const row = await db.send(new GetCommand({ TableName: SUBSCRIPTIONS_TABLE, Key: { user_id: userId } }));
    const customerId = row.Item?.stripe_customer_id;
    if (!customerId) {
      return response(404, { error: "No subscription found for this account yet" });
    }

    const secretKey = await getStripeSecretKey();
    const params = new URLSearchParams();
    params.set("customer", customerId);
    params.set("return_url", `${APP_ORIGIN}/`);

    const stripeResp = await fetch("https://api.stripe.com/v1/billing_portal/sessions", {
      method: "POST",
      headers: {
        Authorization: `Basic ${Buffer.from(`${secretKey}:`).toString("base64")}`,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: params.toString(),
    });

    const session = await stripeResp.json();
    if (!stripeResp.ok) {
      console.error("Stripe error creating portal session:", session);
      return response(502, { error: session.error?.message || "Stripe request failed" });
    }

    return response(200, { url: session.url });
  } catch (err) {
    console.error("createPortalSession error:", err);
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
