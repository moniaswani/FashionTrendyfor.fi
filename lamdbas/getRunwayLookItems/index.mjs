// GET /runway-looks/{look_id}/items — public, no auth. Backs the gallery's
// detail-modal fetch (ui_prototypes/runway-gallery's LookDetail.tsx),
// replacing the prototype's static by-show/{designer}--{season}.json files
// with a direct RunwayItems query scoped to one look.

import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, QueryCommand } from "@aws-sdk/lib-dynamodb";

const REGION = "eu-west-2";
const TABLE_NAME = "RunwayItems";

const client = new DynamoDBClient({ region: REGION });
const db = DynamoDBDocumentClient.from(client);

export const handler = async (event) => {
  try {
    const lookId = event.pathParameters?.look_id;
    if (!lookId) return response(400, { error: "Missing look_id" });

    const result = await db.send(
      new QueryCommand({
        TableName: TABLE_NAME,
        KeyConditionExpression: "look_id = :lid",
        ExpressionAttributeValues: { ":lid": lookId },
      })
    );

    // Mirrors the Item type in ui_prototypes/runway-gallery/src/types.ts.
    const items = (result.Items ?? [])
      .sort((a, b) => a.item_index - b.item_index)
      .map((it) => ({
        item_name: it.item_name ?? null,
        color: it.color ?? null,
        material: it.material ?? null,
        item_label: it.item_label ?? null,
      }));

    return response(200, items);
  } catch (err) {
    console.error("getRunwayLookItems error:", err);
    return response(500, { error: err.message || "Internal error" });
  }
};

function response(statusCode, body) {
  return {
    statusCode,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Headers": "Content-Type",
    },
    body: JSON.stringify(body),
  };
}
