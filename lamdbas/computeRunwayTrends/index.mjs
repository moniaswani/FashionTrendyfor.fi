// Triggered nightly by EventBridge (see template.yaml). Scans RunwayLooks
// (item_names/colors/materials/mood_keywords are already denormalized onto
// each look — see src/excel_to_dynamodb.py) and writes a precomputed
// runway_trends.json to S3 — read directly (no Lambda in that path) by
// both project/src/components/TrendsDashboard.tsx (aggregate only) and
// ui_prototypes/runway-gallery/src/components/TrendsPage.tsx (aggregate +
// per-designer, via the by_designer section).
//
// The share/delta/direction math, and the per-designer volume-scaling of
// the items-category threshold, port
// ui_prototypes/runway-gallery/src/lib/trends.ts's computeTrends() and
// TrendsPage.tsx's volumeScale logic — keep the three in sync if that
// logic changes.

import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, paginateScan } from "@aws-sdk/lib-dynamodb";
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import { gzipSync } from "node:zlib";

const REGION = "eu-west-2";
const LOOKS_TABLE = "RunwayLooks";
const CACHE_BUCKET = "fashion-trends-cache";
const OUTPUT_KEY = "runway_trends.json";

const CATEGORY_FIELDS = {
  colors: "colors",
  items: "item_names",
  materials: "materials",
  moods: "mood_keywords",
};
// "items" has 1,700+ distinct raw names — most appear a handful of times
// and would produce meaningless 100%-swing "trends". Matches the same
// threshold in ui_prototypes/runway-gallery/src/lib/trends.ts.
const DEFAULT_MIN_TOTAL_FOR_ITEMS = 30;
const RISING_PP = 1.5;
const FALLING_PP = -1.5;

const SEASON_RE = /^(spring|fall)-(summer|winter)-(\d{4})$/;
function seasonSortKey(seasonLower) {
  const m = SEASON_RE.exec(seasonLower);
  if (!m) return 0;
  const year = parseInt(m[3], 10);
  return year + (m[1] === "spring" ? 0 : 0.5);
}
function seasonShortLabel(season) {
  const lower = season.toLowerCase();
  const yearMatch = lower.match(/(\d{4})/);
  const yy = yearMatch ? yearMatch[1].slice(-2) : "??";
  if (lower.includes("spring")) return `SS${yy}`;
  if (lower.includes("fall")) return `FW${yy}`;
  return season;
}

const client = new DynamoDBClient({ region: REGION });
const db = DynamoDBDocumentClient.from(client);
const s3 = new S3Client({ region: REGION });

export const handler = async () => {
  const looks = [];
  for await (const page of paginateScan({ client: db }, { TableName: LOOKS_TABLE })) {
    for (const row of page.Items ?? []) looks.push(row);
  }

  const aggregate = computeScope(looks, looks.length);

  const byDesigner = {};
  const looksByDesigner = new Map();
  for (const l of looks) {
    if (!l.designer) continue;
    if (!looksByDesigner.has(l.designer)) looksByDesigner.set(l.designer, []);
    looksByDesigner.get(l.designer).push(l);
  }
  for (const [designer, designerLooks] of looksByDesigner) {
    byDesigner[designer] = computeScope(designerLooks, looks.length);
  }

  const output = {
    generated_at: new Date().toISOString(),
    ...aggregate,
    by_designer: byDesigner,
  };

  const body = gzipSync(Buffer.from(JSON.stringify(output)));
  await s3.send(
    new PutObjectCommand({
      Bucket: CACHE_BUCKET,
      Key: OUTPUT_KEY,
      Body: body,
      ContentType: "application/json",
      ContentEncoding: "gzip",
    })
  );

  console.log(`Wrote runway trends: ${looks.length} looks, ${looksByDesigner.size} designers`);
  return { looksScanned: looks.length, designers: looksByDesigner.size };
};

// One scope's worth of output — either every look (aggregate) or one
// designer's looks. `totalLooksAllScopes` is always the full dataset's
// look count, used only to scale the items-category volume threshold.
function computeScope(scopeLooks, totalLooksAllScopes) {
  const seasonDisplay = new Map();
  for (const l of scopeLooks) if (l.season_lower && l.season) seasonDisplay.set(l.season_lower, l.season);
  const seasons = [...seasonDisplay.entries()]
    .sort((a, b) => seasonSortKey(a[0]) - seasonSortKey(b[0]))
    .map(([lower, display]) => ({ lower, display, short: seasonShortLabel(display) }));

  const totalsBySeason = new Map(seasons.map((s) => [s.lower, 0]));
  for (const l of scopeLooks) {
    if (l.season_lower && totalsBySeason.has(l.season_lower)) {
      totalsBySeason.set(l.season_lower, totalsBySeason.get(l.season_lower) + 1);
    }
  }

  const overall = {};
  for (const s of seasons) overall[s.display] = totalsBySeason.get(s.lower) ?? 0;

  // Mirrors TrendsPage.tsx: a single designer has far fewer looks per
  // season than the whole dataset, so the "needs real volume" noise filter
  // for items must scale down too, or every item gets excluded.
  const volumeScale = totalLooksAllScopes > 0 ? Math.max(scopeLooks.length / totalLooksAllScopes, 0.05) : 1;
  const minTotalForItems = Math.max(5, Math.round(DEFAULT_MIN_TOTAL_FOR_ITEMS * volumeScale));

  const categories = {};
  for (const [category, field] of Object.entries(CATEGORY_FIELDS)) {
    categories[category] = computeSeries(scopeLooks, field, seasons, totalsBySeason, category === "items" ? minTotalForItems : 0);
  }

  return {
    seasons: seasons.map((s) => s.display),
    total_looks: scopeLooks.length,
    overall,
    categories,
  };
}

function computeSeries(looks, field, seasons, totalsBySeason, minTotal) {
  const countsByEntity = new Map();
  for (const look of looks) {
    const values = new Set(look[field] ?? []);
    for (const v of values) {
      if (!countsByEntity.has(v)) countsByEntity.set(v, new Map());
      const bySeason = countsByEntity.get(v);
      bySeason.set(look.season_lower, (bySeason.get(look.season_lower) ?? 0) + 1);
    }
  }

  const series = [];
  for (const [name, bySeason] of countsByEntity) {
    const totalCount = [...bySeason.values()].reduce((a, b) => a + b, 0);
    if (minTotal > 0 && totalCount < minTotal) continue;

    const points = seasons.map((s) => {
      const count = bySeason.get(s.lower) ?? 0;
      const total = totalsBySeason.get(s.lower) ?? 0;
      return { season: s.display, shortLabel: s.short, share: total > 0 ? (count / total) * 100 : 0, count };
    });

    const withData = points.map((p, i) => ({ ...p, i })).filter((p) => p.count > 0);
    let deltaPP = 0;
    if (withData.length >= 2) {
      const last = withData[withData.length - 1];
      const prev = withData[withData.length - 2];
      deltaPP = last.share - prev.share;
    } else if (withData.length === 1 && withData[0].i === points.length - 1) {
      deltaPP = withData[0].share;
    }
    const direction = deltaPP > RISING_PP ? "rising" : deltaPP < FALLING_PP ? "falling" : "stable";

    const latest = points[points.length - 1];
    series.push({
      name,
      totalCount,
      points,
      latestShare: latest?.share ?? 0,
      latestCount: latest?.count ?? 0,
      deltaPP,
      direction,
    });
  }
  return series;
}
