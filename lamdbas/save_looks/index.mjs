import crypto from "crypto";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, PutCommand } from "@aws-sdk/lib-dynamodb";

const client = new DynamoDBClient({ region: "eu-west-2" });
const db = DynamoDBDocumentClient.from(client);

const TABLE_NAME = "MoonboardLooks";

const filterSet = (arr) =>
  Array.isArray(arr) ? arr.filter(Boolean) : [];

export const handler = async (event) => {
  try {
    const userId = event.requestContext?.authorizer?.jwt?.claims?.sub;
    if (!userId) {
      return response(401, { error: "Unauthorized" });
    }

    const body = JSON.parse(event.body || "{}");

    const requiredFields = [
      "image_id",
      "designer",
      "season",
      "original_image_name",
      "image_url",
    ];

    for (const field of requiredFields) {
      if (!body[field]) {
        return response(400, { error: `Missing required field: ${field}` });
      }
    }

    const lookId = crypto.randomUUID();
    const now = new Date().toISOString();
    const folderToken = body.folder_id || "uncategorized";

    const item = {
      user_id: userId,
      look_id: lookId,
      image_id: body.image_id,
      designer: body.designer,
      season: body.season,
      original_image_name: body.original_image_name,
      image_url: body.image_url,
      saved_at: now,
      GSI1PK: userId,
      GSI1SK: `${folderToken}#${now}#${lookId}`,
      items: filterSet(body.items),
      colors: filterSet(body.colors),
      materials: filterSet(body.materials),
      ...(body.folder_id ? { folder_id: body.folder_id } : {}), // optional
    };

    await db.send(
      new PutCommand({
        TableName: TABLE_NAME,
        Item: item,
        ConditionExpression: "attribute_not_exists(user_id) AND attribute_not_exists(look_id)", // safety
      })
    );

    return response(200, {
      success: true,
      look_id: lookId,
    });
  } catch (err) {
    console.error("Save Lambda error:", err);
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
