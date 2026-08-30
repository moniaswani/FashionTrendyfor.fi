// GET /runway-likes — authenticated. Returns every look_id the caller has
// liked, newest first. Deliberately returns just {look_id, liked_at} pairs
// rather than full look data — the frontend already holds the full index
// (runway_looks_index.json) in memory and cross-references by look_id,
// same pattern ui_prototypes/runway-gallery's useLikes hook already used
// for its localStorage-only version of this.

import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, QueryCommand } from "@aws-sdk/lib-dynamodb";

const REGION = "eu-west-2";
const TABLE_NAME = "RunwayLikes";

const client = new DynamoDBClient({ region: REGION });
const db = DynamoDBDocumentClient.from(client);

export const handler = async (event) => {
  try {
    const userId = event.requestContext?.authorizer?.jwt?.claims?.sub;
    if (!userId) return response(401, { error: "Unauthorized" });

    const result = await db.send(
      new QueryCommand({
        TableName: TABLE_NAME,
        KeyConditionExpression: "user_id = :uid",
        ExpressionAttributeValues: { ":uid": userId },
      })
    );

    const items = (result.Items ?? [])
      .map((it) => ({ look_id: it.look_id, liked_at: it.liked_at }))
      .sort((a, b) => new Date(b.liked_at).getTime() - new Date(a.liked_at).getTime());

    return response(200, items);
  } catch (err) {
    console.error("getLikedLooks error:", err);
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
