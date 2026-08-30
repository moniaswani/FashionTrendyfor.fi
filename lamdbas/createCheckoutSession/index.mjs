// POST /billing/checkout-session — authenticated (same Cognito JWT
// authorizer as toggleLike, pool eu-west-2_sCT3ddeep). Creates a Stripe
// Checkout Session (hosted full-page, subscription mode — GBP 1.99/month,
// 30-day free trial) and returns its redirect URL. The frontend just
// does window.location.href = url; Stripe hosts the actual payment form.
//
// The Stripe secret key is never a Lambda env var — fetched from SSM
// Parameter Store (SecureString) at runtime and cached in memory for the
// lifetime of the execution environment, so it's readable only by this
// function's own IAM role, not visible via lambda:GetFunctionConfiguration.

import { SSMClient, GetParameterCommand } from "@aws-sdk/client-ssm";

const REGION = "eu-west-2";
const STRIPE_SECRET_PARAM = "/runway-gallery/stripe-secret-key";
const PRICE_ID = "price_1U8eUgRqfP1gbqgEy47nIcQ2"; // "Runway Gallery Access", GBP 1.99/month
const TRIAL_DAYS = 30;

// Where Stripe should send the browser after checkout succeeds/is cancelled.
// Overridable via env var so this works from both localhost and a deployed
// origin without a code change; falls back to the known dev origin.
const APP_ORIGIN = process.env.APP_ORIGIN || "http://localhost:5173";

const ssm = new SSMClient({ region: REGION });
let cachedSecretKey = null;

async function getStripeSecretKey() {
  if (cachedSecretKey) return cachedSecretKey;
  const resp = await ssm.send(
    new GetParameterCommand({ Name: STRIPE_SECRET_PARAM, WithDecryption: true })
  );
  cachedSecretKey = resp.Parameter.Value;
  return cachedSecretKey;
}

export const handler = async (event) => {
  try {
    const userId = event.requestContext?.authorizer?.jwt?.claims?.sub;
    const email = event.requestContext?.authorizer?.jwt?.claims?.email;
    if (!userId) return response(401, { error: "Unauthorized" });

    const secretKey = await getStripeSecretKey();

    const params = new URLSearchParams();
    params.set("mode", "subscription");
    params.set("line_items[0][price]", PRICE_ID);
    params.set("line_items[0][quantity]", "1");
    params.set("subscription_data[trial_period_days]", String(TRIAL_DAYS));
    // Ties the eventual webhook events (which only carry Stripe customer/
    // subscription IDs) back to this Cognito user.
    params.set("client_reference_id", userId);
    if (email) params.set("customer_email", email);
    params.set("success_url", `${APP_ORIGIN}/?checkout=success`);
    params.set("cancel_url", `${APP_ORIGIN}/?checkout=cancelled`);
    // Lets Stripe's own hosted Checkout page show an "Add promotion code"
    // field, for admin-issued codes (e.g. LAUNCH2026, BESTIE1) created and
    // fully managed from the Stripe Dashboard (Product catalog -> Coupons /
    // Promotion codes) — no code change needed to add, edit, or deactivate
    // one. A one-time custom peer-to-peer referral system (a unique code
    // minted per user, DynamoDB-tracked) was built and then retired same
    // day in favor of this — a single shared code is simpler and avoids the
    // confusion of two different "enter a code" surfaces on one flow.
    params.set("allow_promotion_codes", "true");
    // This Stripe account has Managed Payments on by default, which
    // requires a tax_code on the product (a real tax classification —
    // not something to guess here). Opting this session out rather than
    // picking one; re-enable once a proper tax_code is set on the product
    // if automatic VAT/sales-tax handling is wanted.
    params.set("managed_payments[enabled]", "false");

    const stripeResp = await fetch("https://api.stripe.com/v1/checkout/sessions", {
      method: "POST",
      headers: {
        Authorization: `Basic ${Buffer.from(`${secretKey}:`).toString("base64")}`,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: params.toString(),
    });

    const session = await stripeResp.json();
    if (!stripeResp.ok) {
      console.error("Stripe error creating checkout session:", session);
      return response(502, { error: session.error?.message || "Stripe request failed" });
    }

    return response(200, { url: session.url });
  } catch (err) {
    console.error("createCheckoutSession error:", err);
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
