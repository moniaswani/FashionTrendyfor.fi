import boto3
import base64
import json
from datetime import datetime
import ast
from io import BytesIO
from PIL import Image

# --- AWS Config ---
bucket_name = "runwayimages"  # ✅ S3 bucket name only
prefix = "acne-studios-ready-to-wear-spring-summer-2024-paris/"  # ✅ folder in the bucket
region = "eu-west-2"
table_name = "FashionAnalysis"

# --- AWS Clients ---
s3 = boto3.client("s3", region_name=region)
bedrock = boto3.client("bedrock-runtime", region_name=region)
dynamodb = boto3.resource("dynamodb", region_name=region)
table = dynamodb.Table(table_name)

# --- Runway date (set manually per collection) ---
RUNWAY_DATE = "March 11, 2025 2:00 pm"
RUNWAY_DATE_ISO = datetime.strptime(RUNWAY_DATE, "%B %d, %Y %I:%M %p").isoformat()


# --- Payload: metadata extraction ---
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
You are a fashion data parser.
Given the following runway image filename, extract structured metadata.

Filename: {filename}

Return valid JSON with these fields:
{{
  "designer": "...",       // Full designer name (e.g., "Louis Vuitton", "Miu Miu")
  "collection": "...",     // Collection name (e.g., "Ready To Wear", "Haute Couture")
  "season": "...",         // Season and year (e.g., "Fall Winter 2025")
  "event": "..."           // Fashion Week event (e.g., "Paris Fashion Week")
}}
Only return JSON, no explanation.
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
        "max_tokens": 1000,
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
                            "You are a fashion analyst. Analyze the image and return structured JSON data.\n\n"
                            "Rules:\n"
                            "- Each clothing item name must be **one single noun**, no adjectives (e.g. 'jacket', 'dress', 'boots').\n"
                            "- Each color name must be **one word**, no modifiers or adjectives (e.g. 'blue', not 'dark blue').\n"
                            "- Each item has only **one** material and one color.\n\n"
                            "Return valid JSON in this exact format:\n"
                            "{\n"
                            "  \"clothing_items\": [\"jacket\", \"pants\", ...],\n"
                            "  \"material_decomposition\": { \"jacket\": \"leather\", \"pants\": \"cotton\", ... },\n"
                            "  \"item_colors_hex\": { \"jacket\": \"#0000FF\", \"pants\": \"#FFFFFF\", ... },\n"
                            "  \"item_colors_name\": { \"jacket\": \"blue\", \"pants\": \"white\", ... }\n"
                            "}\n\n"
                            "Be concise, lowercase all keys, and return only valid JSON — no text outside JSON."
                        )
                    }
                ]
            }
        ]
    }


# --- Helper: preprocess + base64 encode image ---
def preprocess_image(image_bytes):
    """Ensure image is valid, RGB, resized, and safely base64-encoded."""
    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        if img.size[0] > 1024 or img.size[1] > 1024:
            img.thumbnail((1024, 1024))
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"⚠️ Image preprocessing failed: {e}")
        return None


# --- Get all image keys from the folder ---
response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
images = [
    obj["Key"]
    for obj in response.get("Contents", [])
    if obj["Key"].lower().endswith((".jpg", ".jpeg", ".png"))
]

print(f"📸 Found {len(images)} images in {prefix}")


# --- Process each image ---
for key in images:
    try:
        print(f"\n🔍 Processing: {key}")
        filename = key.split("/")[-1]

        # Step 1: Metadata extraction (Claude)
        meta_payload = create_metadata_payload(filename)
        meta_response = bedrock.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(meta_payload)
        )
        meta_result = json.loads(meta_response["body"].read())
        meta_text = meta_result["content"][0]["text"]

        try:
            meta = json.loads(meta_text)
        except json.JSONDecodeError:
            meta = ast.literal_eval(meta_text)

        # Step 2: Image analysis
        s3_obj = s3.get_object(Bucket=bucket_name, Key=key)
        image_bytes = s3_obj["Body"].read()

        image_b64 = preprocess_image(image_bytes)
        if not image_b64:
            print(f"❌ Skipping {key}: invalid or unsupported image")
            continue

        analysis_payload = create_analysis_payload(image_b64)
        analysis_response = bedrock.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(analysis_payload)
        )
        analysis_result = json.loads(analysis_response["body"].read())
        analysis_text = analysis_result["content"][0]["text"]

        try:
            structured_data = json.loads(analysis_text)
        except json.JSONDecodeError:
            structured_data = ast.literal_eval(analysis_text)

        clothing_items = structured_data.get("clothing_items", [])
        materials = structured_data.get("material_decomposition", {})
        colors_hex = structured_data.get("item_colors_hex", {})
        colors_name = structured_data.get("item_colors_name", {})

        timestamp = datetime.utcnow().isoformat()

        # Step 3: Store results in DynamoDB
        for item in clothing_items:
            safe_item = item.replace(" ", "_").lower()
            image_id = f"{filename}_{safe_item}"

            # 🧠 Extract brand from filename if Claude misses it
            filename_lower = filename.lower()
            brand_prefix = (
                filename_lower.split("ready-to-wear")[0]
                .split("readytowear")[0]
                .strip("-_ ")
                .capitalize()
            )

            entry = {
                "image_id": image_id,
                "original_image_name": filename,
                "timestamp": timestamp,
                "item_name": item,
                "materials": materials.get(item, "unknown"),
                "color_hex": colors_hex.get(item, "unknown"),
                "color_name": colors_name.get(item, "unknown"),
                "designer": meta.get("designer", brand_prefix or "unknown"),
                "collection": meta.get("collection", "unknown"),
                "season": meta.get("season", "unknown"),
                "event": meta.get("event", "unknown"),
                "runway_date": RUNWAY_DATE_ISO,
            }

            print(f"⬆️ Uploading: {image_id}")
            table.put_item(Item=entry)

    except Exception as e:
        print(f"❌ Error processing {key}: {str(e)}")

print("\n✅ All images processed.")
