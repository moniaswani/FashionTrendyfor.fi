// Two routes, one handler:
//   POST /images/sign          — behind CognitoAuthorizer (real, verified JWT).
//                                 Entitled callers get every requested look_id
//                                 signed, no cap.
//   POST /images/sign-preview  — public, no authorizer. Hard-capped at
//                                 PREVIEW_CAP look_ids server-side regardless
//                                 of what's requested — this is what the
//                                 anonymous top-50 gallery preview calls.
//
// `runwayimages` is a private S3 bucket (no public bucket policy) — this is
// the only path that can produce a working image URL. Presigned URLs are
// valid based on this Lambda's own execution-role permissions, independent
// of the bucket's public-access settings, which is what makes it safe to
// build and verify this whole path before the bucket was ever made private.
//
// Known accepted limitation: the sign-preview cap is a soft deterrent, not
// real enforcement — nothing stops repeated anonymous calls with different
// batches of 50. Proper rate-limiting (API Gateway usage plans/WAF) would be
// the next hardening step if this ever becomes a real problem, not built now.

import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, GetCommand } from "@aws-sdk/lib-dynamodb";

const REGION = "eu-west-2";
const BUCKET = "runwayimages";
const SUBSCRIPTIONS_TABLE = "RunwaySubscriptions";
const PREVIEW_CAP = 50;
const MAX_PER_REQUEST = 500; // sanity ceiling even for entitled callers
const URL_EXPIRY_SECONDS = 3600;
const ENTITLED_STATUSES = new Set(["trialing", "active"]);

const s3 = new S3Client({ region: REGION });
const db = DynamoDBDocumentClient.from(new DynamoDBClient({ region: REGION }));

async function signLookIds(lookIds) {
  const entries = await Promise.all(
    lookIds.map(async (lookId) => {
      const command = new GetObjectCommand({ Bucket: BUCKET, Key: `${lookId}.jpg` });
      const url = await getSignedUrl(s3, command, { expiresIn: URL_EXPIRY_SECONDS });
      return [lookId, url];
    }),
  );
  return Object.fromEntries(entries);
}

export const handler = async (event) => {
  try {
    let lookIds;
    try {
      lookIds = JSON.parse(event.body || "{}").look_ids;
    } catch {
      return response(400, { error: "Invalid JSON body" });
    }
    if (!Array.isArray(lookIds) || lookIds.some((id) => typeof id !== "string")) {
      return response(400, { error: "look_ids must be an array of strings" });
    }

    const userId = event.requestContext?.authorizer?.jwt?.claims?.sub;
    const isPreviewRoute = event.rawPath?.endsWith("/sign-preview") ?? false;

    if (isPreviewRoute) {
      const capped = lookIds.slice(0, PREVIEW_CAP);
      return response(200, { urls: await signLookIds(capped) });
    }

    // /images/sign — CognitoAuthorizer already guarantees userId is a real,
    // verified sub. Still re-check entitlement server-side rather than
    // trusting the UI to only ever call this when it should.
    if (!userId) return response(401, { error: "Unauthorized" });

    const sub = await db.send(new GetCommand({ TableName: SUBSCRIPTIONS_TABLE, Key: { user_id: userId } }));
    const entitled = sub.Item && ENTITLED_STATUSES.has(sub.Item.status);
    if (!entitled) return response(403, { error: "Not entitled" });

    const capped = lookIds.slice(0, MAX_PER_REQUEST);
    return response(200, { urls: await signLookIds(capped) });
  } catch (err) {
    console.error("getSignedImageUrls error:", err);
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
