import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, QueryCommand } from "@aws-sdk/lib-dynamodb";

const client = new DynamoDBClient({ region: "eu-west-2" });
const db = DynamoDBDocumentClient.from(client);

const TABLE_NAME = "MoonboardLooks";
const GSI1_NAME = "GSI1";

export const handler = async (event) => {
  try {
    const userId = event.requestContext?.authorizer?.jwt?.claims?.sub;
    if (!userId) return response(401, { error: "Unauthorized" });

    const folderId = event.queryStringParameters?.folder_id?.trim();

    let result;
    if (folderId) {
      // Folder-specific query via GSI1
      result = await db.send(
        new QueryCommand({
          TableName: TABLE_NAME,
          IndexName: GSI1_NAME,
          KeyConditionExpression: "GSI1PK = :uid AND begins_with(GSI1SK, :prefix)",
          ExpressionAttributeValues: {
            ":uid": userId,
            ":prefix": `${folderId}#`,
          },
          ScanIndexForward: false, // newest by saved_at in GSI1SK
        })
      );
      return response(200, result.Items || []);
    }

    // All looks for user (base table)
    result = await db.send(
      new QueryCommand({
        TableName: TABLE_NAME,
        KeyConditionExpression: "user_id = :uid",
        ExpressionAttributeValues: { ":uid": userId },
      })
    );

    // Base SK is UUID, so sort in app by saved_at
    const items = (result.Items || []).sort(
      (a, b) => new Date(b.saved_at).getTime() - new Date(a.saved_at).getTime()
    );

    return response(200, items);
  } catch (err) {
    console.error("Get Lambda error:", err);
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
