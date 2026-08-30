// Triggered by RunwayLooks' DynamoDB Stream (see template.yaml). Scans the
// whole table and rewrites the public gallery cache on S3 — runway_looks_index.json
// (drop-in replacement for ui_prototypes/runway-gallery's index.json) and
// runway_facets.json (replacement for facets.json). Full rescan each run,
// so it's safe to invoke repeatedly (idempotent overwrite) or manually.
//
// ReservedConcurrentExecutions is pinned to 1 in template.yaml: a bulk
// write (e.g. src/backfill_runway_looks_facets.py) fires many stream
// records, but each of those triggers a full-table scan, so only one
// regen should ever run at a time — extra queued invocations just repeat
// the same idempotent overwrite once the first finishes.

import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, paginateScan } from "@aws-sdk/lib-dynamodb";
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import { gzipSync } from "node:zlib";

const REGION = "eu-west-2";
const LOOKS_TABLE = "RunwayLooks";
const CACHE_BUCKET = "fashion-trends-cache";
const INDEX_KEY = "runway_looks_index.json";
const FACETS_KEY = "runway_facets.json";

// Mirrors IndexLook in ui_prototypes/runway-gallery/src/types.ts.
const SCALAR_FIELDS = [
  "look_id", "designer", "designer_lower", "season", "season_lower",
  "collection", "event", "city", "look_number",
];
const LIST_FIELDS = ["color_palette_hex", "mood_keywords", "item_names", "colors", "materials"];

const client = new DynamoDBClient({ region: REGION });
const db = DynamoDBDocumentClient.from(client);
const s3 = new S3Client({ region: REGION });

export const handler = async () => {
  const index = [];
  const designers = new Set();
  const seasons = new Set();
  const items = new Set();
  const colors = new Set();
  const materials = new Set();

  for await (const page of paginateScan({ client: db }, { TableName: LOOKS_TABLE })) {
    for (const row of page.Items ?? []) {
      const entry = {};
      for (const field of SCALAR_FIELDS) entry[field] = row[field] ?? null;
      for (const field of LIST_FIELDS) entry[field] = row[field] ?? [];
      entry.like_count = row.like_count ?? 0; // written by toggleLike (Phase 2)
      index.push(entry);

      if (row.designer) designers.add(row.designer);
      if (row.season) seasons.add(row.season);
      for (const v of row.item_names ?? []) items.add(v);
      for (const v of row.colors ?? []) colors.add(v);
      for (const v of row.materials ?? []) materials.add(v);
    }
  }

  const facets = {
    designers: [...designers].sort(),
    seasons: [...seasons].sort(),
    items: [...items].sort(),
    colors: [...colors].sort(),
    materials: [...materials].sort(),
  };

  await Promise.all([putJsonGzip(INDEX_KEY, index), putJsonGzip(FACETS_KEY, facets)]);

  console.log(`Regenerated runway gallery cache: ${index.length} looks`);
  return { looksWritten: index.length };
};

async function putJsonGzip(key, data) {
  const body = gzipSync(Buffer.from(JSON.stringify(data)));
  await s3.send(
    new PutObjectCommand({
      Bucket: CACHE_BUCKET,
      Key: key,
      Body: body,
      ContentType: "application/json",
      ContentEncoding: "gzip",
    })
  );
}
