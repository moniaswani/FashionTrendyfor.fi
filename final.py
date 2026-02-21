import boto3
import base64
import json
import ast
from datetime import datetime
from boto3.dynamodb.conditions import Attr
from io import BytesIO
from PIL import Image

# ---------------- AWS CONFIG ----------------
BUCKET_NAME = "runwayimages"
REGION = "eu-west-2"
TABLE_NAME = "FashionAnalysis"

RUNWAY_DATE = "October 6, 2025 2:00 pm"
RUNWAY_DATE_ISO = datetime.strptime(
    RUNWAY_DATE, "%B %d, %Y %I:%M %p"
).isoformat()

# ---------------- CLIENTS ----------------
s3 = boto3.client("s3", region_name=REGION)
bedrock = boto3.client("bedrock-runtime", region_name=REGION)
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)



# ---------------- HELPERS ----------------
def list_collection_prefixes(bucket_name: str):
    paginator = s3.get_paginator("list_objects_v2")
    prefixes = set()

    for page in paginator.paginate(
        Bucket=bucket_name,
        Delimiter="/"
    ):
        for cp in page.get("CommonPrefixes", []):
            prefixes.add(cp["Prefix"])

    return sorted(prefixes)


def image_already_processed(filename: str) -> bool:
    last_key = None

    while True:
        scan_kwargs = {
            "FilterExpression": Attr("original_image_name").eq(filename),
            "ProjectionExpression": "image_id",
        }
        if last_key:
            scan_kwargs["ExclusiveStartKey"] = last_key

        resp = table.scan(**scan_kwargs)

        if resp.get("Items"):
            return True  # found at least one row for this image

        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            return False  # scanned entire table, no match


def preprocess_image(image_bytes):
    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        img.thumbnail((1024, 1024))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"⚠️ Image preprocessing failed: {e}")
        return None


# --- Payload: metadata extraction ---
# --- Payload: metadata extraction (STRICT) ---
def create_metadata_payload(filename: str):
        return {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""
    You are a highly accurate fashion metadata extraction engine.

    Your ONLY input is the runway image filename below.
    You must extract ALL possible metadata implied by the filename.
    Do NOT guess beyond filename evidence.

    Filename:
    {filename}

    Instructions:
    - Parse designer, collection type, season + year, and fashion event from the filename.
    - Use standard fashion naming conventions.
    - If a field is not explicitly present, infer it ONLY if it is unambiguous.
    - If truly unavailable, return "unknown" (never null, never empty).
    - Capitalize proper nouns correctly (e.g. "Miu Miu", "Paris Fashion Week").
    - Season format MUST be: "Spring Summer YYYY" or "Fall Winter YYYY".

    Return ONLY valid JSON in exactly this schema:

    {{
    "designer": "Full designer name or unknown",
    "collection": "Ready To Wear | Haute Couture | Menswear | unknown",
    "season": "Season Year or unknown",
    "event": "Fashion week event or unknown"
    }}

    Do not include explanations, comments, or extra text.
    Only output valid JSON.
    """
                        }
                    ]
                }
            ]
        }



# --- Payload: image analysis ---
def create_analysis_payload(image_b64):
    return {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1200,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_b64
                        }
                    },
                    {
                        "type": "text",
                        "text": (
                            "You are a highly precise fashion image parsing system.\n\n"
                            "TASK:\n"
                            "Identify EVERY distinct clothing or wearable item visible on the model.\n"
                            "Do not miss layers, accessories, footwear, or secondary garments.\n\n"

                            "DEFINITION OF ITEM:\n"
                            "- Any separate wearable object counts as an item\n"
                            "- Examples: jacket, coat, shirt, top, trousers, skirt, dress, boots, shoes, bag, belt, scarf\n"
                            "- If two items are visually separate, they MUST be listed separately\n\n"

                            "STRICT RULES:\n"
                            "- Each item name MUST be a single lowercase noun (no adjectives)\n"
                            "- No combined items (❌ 'jacket-and-shirt')\n"
                            "- Each item MUST have exactly one material and one color\n"
                            "- Color names MUST be one word (e.g. 'black', 'red')\n"
                            "- Hex color MUST accurately represent the dominant visible color\n\n"

                            "COMPLETENESS CHECK:\n"
                            "- Before answering, verify that every visible garment has been included\n"
                            "- If unsure whether something counts, INCLUDE IT\n\n"

                            "RETURN EXACTLY THIS JSON FORMAT:\n"
                            "{\n"
                            "  \"clothing_items\": [\"item1\", \"item2\", \"item3\"],\n"
                            "  \"material_decomposition\": {\n"
                            "    \"item1\": \"material\",\n"
                            "    \"item2\": \"material\"\n"
                            "  },\n"
                            "  \"item_colors_hex\": {\n"
                            "    \"item1\": \"#RRGGBB\",\n"
                            "    \"item2\": \"#RRGGBB\"\n"
                            "  },\n"
                            "  \"item_colors_name\": {\n"
                            "    \"item1\": \"color\",\n"
                            "    \"item2\": \"color\"\n"
                            "  }\n"
                            "}\n\n"

                            "IMPORTANT:\n"
                            "- All keys must be lowercase\n"
                            "- Every item in clothing_items MUST appear in ALL three mappings\n"
                            "- Output ONLY valid JSON\n"
                            "- No commentary, no markdown, no extra text"
                        )
                    }
                ]
            }
        ]
    }


# ---------------- MAIN PIPELINE ----------------
collection_prefixes = list_collection_prefixes(BUCKET_NAME)
print(f"📂 Found {len(collection_prefixes)} collections")

for prefix in collection_prefixes:
    print(f"\n📁 Processing collection: {prefix}")

    response = s3.list_objects_v2(
        Bucket=BUCKET_NAME,
        Prefix=prefix
    )

    images = [
        obj["Key"]
        for obj in response.get("Contents", [])
        if obj["Key"].lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    print(f"📸 Found {len(images)} images")

    for key in images:
        try:
            filename = key.split("/")[-1]

            # ✅ CHECK DYNAMODB FIRST
            if image_already_processed(filename):
                print(f"⏭️ Skipping processed image: {filename}")
                continue

            print(f"\n🔍 Processing: {key}")

            # ---- METADATA ----
            meta_payload = create_metadata_payload(filename)
            meta_response = bedrock.invoke_model(
                modelId="anthropic.claude-3-haiku-20240307-v1:0",
                contentType="application/json",
                accept="application/json",
                body=json.dumps(meta_payload)
            )

            meta_text = json.loads(meta_response["body"].read())["content"][0]["text"]
            meta = json.loads(meta_text)

            # ---- IMAGE ----
            s3_obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
            image_bytes = s3_obj["Body"].read()

            image_b64 = preprocess_image(image_bytes)
            if not image_b64:
                continue

            analysis_payload = create_analysis_payload(image_b64)
            analysis_response = bedrock.invoke_model(
                modelId="anthropic.claude-3-haiku-20240307-v1:0",
                contentType="application/json",
                accept="application/json",
                body=json.dumps(analysis_payload)
            )

            analysis_text = json.loads(analysis_response["body"].read())["content"][0]["text"]
            structured = json.loads(analysis_text)

            timestamp = datetime.utcnow().isoformat()

            for item in structured.get("clothing_items", []):
                image_id = f"{filename}_{item}".lower()

                entry = {
                    "image_id": image_id,
                    "original_image_name": filename,
                    "timestamp": timestamp,
                    "item_name": item,
                    "materials": structured["material_decomposition"].get(item, "unknown"),
                    "color_hex": structured["item_colors_hex"].get(item, "unknown"),
                    "color_name": structured["item_colors_name"].get(item, "unknown"),
                    "designer": meta.get("designer", "unknown"),
                    "collection": meta.get("collection", "unknown"),
                    "season": meta.get("season", "unknown"),
                    "event": meta.get("event", "unknown"),
                    "runway_date": RUNWAY_DATE_ISO,
                }

                print(f"⬆️ Writing: {image_id}")
                table.put_item(Item=entry)

        except Exception as e:
            print(f"❌ Error processing {key}: {e}")


print("\n✅ ALL NEW IMAGES PROCESSED")