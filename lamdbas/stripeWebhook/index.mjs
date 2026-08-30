// POST /billing/webhook — PUBLIC (Stripe calls this directly, no Cognito
// authorizer; authenticity comes from verifying Stripe's own signature
// instead, not from our JWT authorizer). No Stripe SDK used anywhere in
// this repo's Lambdas, so signature verification is done by hand here —
// it's just HMAC-SHA256 over "{timestamp}.{rawBody}", documented at
// https://docs.stripe.com/webhooks#verify-manually
//
// Maintains RunwaySubscriptions (PK user_id, GSI CustomerIndex on
// stripe_customer_id) as the source of truth for gallery access:
//   checkout.session.completed        -> establish user_id <-> customer mapping, status "trialing"
//   customer.subscription.updated     -> refresh status/current_period_end/cancel_at_period_end/paused (looked up via CustomerIndex)
//   customer.subscription.deleted     -> status "canceled"
//
// Until /runway-gallery/stripe-webhook-secret exists in SSM (created after
// the Stripe Dashboard webhook endpoint is set up and gives you the
// signing secret), this fails closed — every event is rejected rather
// than trusted unverified.

import { SSMClient, GetParameterCommand } from "@aws-sdk/client-ssm";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, PutCommand, UpdateCommand, QueryCommand } from "@aws-sdk/lib-dynamodb";
import crypto from "node:crypto";

const REGION = "eu-west-2";
const WEBHOOK_SECRET_PARAM = "/runway-gallery/stripe-webhook-secret";
const SUBSCRIPTIONS_TABLE = "RunwaySubscriptions";
const TOLERANCE_SECONDS = 300; // reject events with a timestamp older than this, replay protection

const ssm = new SSMClient({ region: REGION });
const db = DynamoDBDocumentClient.from(new DynamoDBClient({ region: REGION }));
let cachedWebhookSecret = null;

async function getWebhookSecret() {
  if (cachedWebhookSecret) return cachedWebhookSecret;
  const resp = await ssm.send(
    new GetParameterCommand({ Name: WEBHOOK_SECRET_PARAM, WithDecryption: true })
  );
  cachedWebhookSecret = resp.Parameter.Value;
  return cachedWebhookSecret;
}

function verifySignature(rawBody, signatureHeader, secret) {
  if (!signatureHeader) return false;
  const parts = Object.fromEntries(
    signatureHeader.split(",").map((kv) => kv.split("=").map((s) => s.trim()))
  );
  const timestamp = parts.t;
  const expectedSig = parts.v1;
  if (!timestamp || !expectedSig) return false;

  const age = Math.floor(Date.now() / 1000) - Number(timestamp);
  if (!Number.isFinite(age) || age > TOLERANCE_SECONDS || age < -TOLERANCE_SECONDS) return false;

  const signedPayload = `${timestamp}.${rawBody}`;
  const computedSig = crypto.createHmac("sha256", secret).update(signedPayload, "utf8").digest("hex");

  const a = Buffer.from(computedSig, "hex");
  const b = Buffer.from(expectedSig, "hex");
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}

async function upsertFromCheckoutSession(session) {
  const userId = session.client_reference_id;
  if (!userId) {
    console.warn("checkout.session.completed with no client_reference_id, skipping:", session.id);
    return;
  }
  await db.send(
    new PutCommand({
      TableName: SUBSCRIPTIONS_TABLE,
      Item: {
        user_id: userId,
        stripe_customer_id: session.customer,
        stripe_subscription_id: session.subscription,
        status: "trialing",
        updated_at: new Date().toISOString(),
      },
    })
  );
}

async function updateFromSubscription(subscription, statusOverride) {
  const customerId = subscription.customer;
  const found = await db.send(
    new QueryCommand({
      TableName: SUBSCRIPTIONS_TABLE,
      IndexName: "CustomerIndex",
      KeyConditionExpression: "stripe_customer_id = :cid",
      ExpressionAttributeValues: { ":cid": customerId },
      Limit: 1,
    })
  );
  const row = found.Items?.[0];
  if (!row) {
    console.warn("subscription event for unknown customer, skipping:", customerId);
    return;
  }
  await db.send(
    new UpdateCommand({
      TableName: SUBSCRIPTIONS_TABLE,
      Key: { user_id: row.user_id },
      // cancel_at_period_end/paused let the Account page show "ends on X" /
      // "paused, resume anytime" instead of just a bare status string —
      // pause_collection doesn't change `status` itself (Stripe treats a
      // paused subscription as still active/trialing), so without this the
      // gallery would have no way to tell a normal subscription from a
      // paused one.
      UpdateExpression:
        "SET #s = :status, stripe_subscription_id = :subId, current_period_end = :cpe, cancel_at_period_end = :cape, paused = :paused, updated_at = :now",
      ExpressionAttributeNames: { "#s": "status" },
      ExpressionAttributeValues: {
        ":status": statusOverride || subscription.status,
        ":subId": subscription.id,
        ":cpe": subscription.current_period_end ?? null,
        ":cape": !!subscription.cancel_at_period_end,
        ":paused": !!subscription.pause_collection,
        ":now": new Date().toISOString(),
      },
    })
  );
}

export const handler = async (event) => {
  try {
    const rawBody = event.isBase64Encoded ? Buffer.from(event.body, "base64").toString("utf8") : event.body ?? "";
    const sigHeader = event.headers?.["stripe-signature"] ?? event.headers?.["Stripe-Signature"];

    let secret;
    try {
      secret = await getWebhookSecret();
    } catch (err) {
      console.error("Webhook secret not configured yet:", err.name);
      return response(500, { error: "Webhook not configured" });
    }

    if (!verifySignature(rawBody, sigHeader, secret)) {
      console.error("Signature verification failed");
      return response(400, { error: "Invalid signature" });
    }

    const stripeEvent = JSON.parse(rawBody);

    switch (stripeEvent.type) {
      case "checkout.session.completed":
        await upsertFromCheckoutSession(stripeEvent.data.object);
        break;
      case "customer.subscription.updated":
      case "customer.subscription.created":
        await updateFromSubscription(stripeEvent.data.object);
        break;
      case "customer.subscription.deleted":
        await updateFromSubscription(stripeEvent.data.object, "canceled");
        break;
      default:
        // Ignore anything we didn't subscribe to on purpose.
        break;
    }

    return response(200, { received: true });
  } catch (err) {
    console.error("stripeWebhook error:", err);
    return response(500, { error: err.message || "Internal error" });
  }
};

function response(statusCode, body) {
  return { statusCode, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}
