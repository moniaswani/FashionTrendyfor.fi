// GET /billing/status — authenticated. Returns the caller's own
// subscription status so the frontend can gate the gallery. No row yet
// (never started checkout) is reported the same as "none" — both mean
// "not entitled", the frontend doesn't need to distinguish them.

import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, GetCommand } from "@aws-sdk/lib-dynamodb";

const REGION = "eu-west-2";
const TABLE_NAME = "RunwaySubscriptions";
const ENTITLED_STATUSES = new Set(["trialing", "active"]);

const db = DynamoDBDocumentClient.from(new DynamoDBClient({ region: REGION }));

export const handler = async (event) => {
  try {
    const userId = event.requestContext?.authorizer?.jwt?.claims?.sub;
    if (!userId) return response(401, { error: "Unauthorized" });

    const resp = await db.send(new GetCommand({ TableName: TABLE_NAME, Key: { user_id: userId } }));
    const status = resp.Item?.status ?? "none";

    return response(200, {
      status,
      entitled: ENTITLED_STATUSES.has(status),
      current_period_end: resp.Item?.current_period_end ?? null,
      cancel_at_period_end: resp.Item?.cancel_at_period_end ?? false,
      paused: resp.Item?.paused ?? false,
    });
  } catch (err) {
    console.error("getSubscriptionStatus error:", err);
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
