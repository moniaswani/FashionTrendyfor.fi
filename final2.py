import boto3
import json
import ast
from datetime import datetime
from urllib.parse import unquote_plus
from io import BytesIO
from PIL import Image
import base64

# --- AWS Config ---
BUCKET = "runwayimages"
PREFIX = "balenciaga-ready-to-wear-spring-summer-2026-paris/cropped/"
REGION = "eu-west-2"
TABLE_NAME = "FashionAnalysis"

# --- Constants ---
COLLECTION = "Ready To Wear"
DESIGNER = "Balenciaga"
EVENT = "Paris Fashion Week"
RUNWAY_DATE = "October 6, 2025 2:00 pm"
SEASON = "Spring Summer 2026"
RUNWAY_DATE_ISO = datetime.strptime(RUNWAY_DATE, "%B %d, %Y %I:%M %p").isoformat()

# --- AWS Clients ---
s3 = boto3.client("s3", region_name=REGION)
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)
bedrock = boto3.client("bedrock-runtime", region_name=REGION)

# --- Helper: preprocess + base64 encode image ---
def preprocess_image(image_bytes):
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

# --- LLM Payload ---
def create_analysis_payload(image_b64, coarse_type):
    return {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 700,
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
                        "text": f"""
You are a fashion garment classifier.

The image shows ONE clothing item.
The detected region type is: {coarse_type}

Your tasks:
1. Identify the most specific garment type
2. Identify the primary material
3. Identify the primary color

Rules:
- Garment type must be ONE noun
- Choose ONLY from this list:
  - tops: shirt, blouse, t-shirt, sweater, knitwear, jacket, blazer, coat, hoodie, top
  - bottoms: jeans, trousers, pants, skirt, shorts, leggings
  - one-piece: dress, jumpsuit
  - footwear: boots, heels, sneakers, loafers, sandals, shoes
- If the item is a dress or jumpsuit, choose that even if the region type was "top"
- Material must be ONE noun (e.g. denim, cotton, silk, leather)
- Color name must be ONE word
- Color hex must be valid hex
- No adjectives, no patterns, no explanations

Return ONLY valid JSON:

{{
  "item_name": "...",
  "materials": "...",
  "color_name": "...",
  "color_hex": "..."
}}
"""
                    }
                ]
            }
        ]
    }

# --- List cropped images ---
response = s3.list_objects_v2(Bucket=BUCKET, Prefix=PREFIX)
image_keys = [
    obj["Key"]
    for obj in response.get("Contents", [])
    if obj["Key"].lower().endswith((".jpg", ".jpeg"))
]

print(f"📸 Found {len(image_keys)} cropped images")

# --- Process each crop ---
for key in image_keys:
    try:
        filename = unquote_plus(key.split("/")[-1])

        # Identify coarse type
        if filename.endswith("_top.jpg"):
            coarse_type = "top"
        elif filename.endswith("_bottom.jpg"):
            coarse_type = "bottom"
        elif filename.endswith("_shoes.jpg"):
            coarse_type = "shoes"
        else:
            print(f"⏭️ Skipping unknown crop type: {filename}")
            continue

        # Base image and ID
        base_name = filename.replace(f"_{coarse_type}.jpg", "")
        original_image_name = f"{base_name}.jpg"
        image_id = f"{base_name.lower()}_{coarse_type}"

        print(f"\n🔍 Processing {image_id}")

        # Load image
        s3_obj = s3.get_object(Bucket=BUCKET, Key=key)
        image_bytes = s3_obj["Body"].read()
        image_b64 = preprocess_image(image_bytes)
        if not image_b64:
            print(f"❌ Skipping {key}: preprocessing failed")
            continue

        # LLM call
        payload = create_analysis_payload(image_b64, coarse_type)
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )
        result = json.loads(response["body"].read())
        text = result["content"][0]["text"]

        try:
            analysis = json.loads(text)
        except json.JSONDecodeError:
            analysis = ast.literal_eval(text)

        fine_item = analysis["item_name"]

        # Dress deduplication
        if fine_item == "dress" and coarse_type == "bottom":
            print("⏭️ Skipping bottom crop (dress detected)")
            continue

        # DynamoDB item
        item = {
            "image_id": image_id,
            "collection": COLLECTION,
            "color_hex": analysis["color_hex"],
            "color_name": analysis["color_name"],
            "designer": DESIGNER,
            "event": EVENT,
            "item_name": fine_item,
            "materials": analysis["materials"],
            "original_image_name": original_image_name,
            "runway_date": RUNWAY_DATE_ISO,
            "season": SEASON,
            "timestamp": datetime.utcnow().isoformat(),
        }

        table.put_item(Item=item)
        print(f"⬆️ Uploaded: {image_id}")

    except Exception as e:
        print(f"❌ Error processing {key}: {e}")

print("\n✅ Done processing all cropped images.")
