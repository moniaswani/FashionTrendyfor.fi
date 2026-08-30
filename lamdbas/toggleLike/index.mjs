// POST /runway-looks/{look_id}/like — authenticated (Cognito JWT authorizer
// on RunwayGalleryApi, pool eu-west-2_sCT3ddeep — the pool project/'s live
// AuthContext.tsx actually issues tokens from; NOT the older pool the
// Moonboard save-look authorizer checks, eu-west-2_GUhx1pI4w — those are
// two different pools, worth fixing separately).
//
// Toggles: if the caller already liked this look, un-likes it (delete);
// otherwise likes it (put). Returns the resulting state so the frontend
// doesn't have to guess which way the toggle went.
//
// The like record (RunwayLikes) and the aggregate counter (RunwayLooks.
// like_count) are written in one DynamoDB transaction so they can never
// drift apart (e.g. a crash between two separate writes). like_count then
// rides the existing RunwayLooks Stream -> regenerateRunwayCache pipeline
// into runway_looks_index.json for free — no new read path needed.

import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, GetCommand, TransactWriteCommand } from "@aws-sdk/lib-dynamodb";

const REGION = "eu-west-2";
const LIKES_TABLE = "RunwayLikes";
const LOOKS_TABLE = "RunwayLooks";

const client = new DynamoDBClient({ region: REGION });
const db = DynamoDBDocumentClient.from(client);

export const handler = async (event) => {
  try {
    const userId = event.requestContext?.authorizer?.jwt?.claims?.sub;
    if (!userId) return response(401, { error: "Unauthorized" });

    const lookId = event.pathParameters?.look_id;
    if (!lookId) return response(400, { error: "Missing look_id" });

    const existing = await db.send(
      new GetCommand({ TableName: LIKES_TABLE, Key: { user_id: userId, look_id: lookId } })
    );
    const wasLiked = !!existing.Item;

    await db.send(
      new TransactWriteCommand({
        TransactItems: [
          wasLiked
            ? { Delete: { TableName: LIKES_TABLE, Key: { user_id: userId, look_id: lookId } } }
            : {
                Put: {
                  TableName: LIKES_TABLE,
                  Item: { user_id: userId, look_id: lookId, liked_at: new Date().toISOString() },
                  ConditionExpression: "attribute_not_exists(look_id)",
                },
              },
          {
            Update: {
              TableName: LOOKS_TABLE,
              Key: { look_id: lookId },
              UpdateExpression: "ADD like_count :delta",
              ExpressionAttributeValues: { ":delta": wasLiked ? -1 : 1 },
            },
          },
        ],
      })
    );

    return response(200, { liked: !wasLiked, look_id: lookId });
  } catch (err) {
    console.error("toggleLike error:", err);
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
