import boto3
import base64
import json
from datetime import datetime
import ast

# AWS Config
bucket_name = "runwayimages/chanel-ready-to-wear-spring-winter-2025-paris/"
region = "eu-west-2"
table_name = "FashionAnalysis"

# AWS Clients
s3 = boto3.client("s3", region_name=region)
bedrock = boto3.client("bedrock-runtime", region_name=region)
dynamodb = boto3.resource("dynamodb", region_name=region)
table = dynamodb.Table(table_name)

# --- Runway date (set manually per event/designer) ---
RUNWAY_DATE = "March 11, 2025 2:00 pm"
RUNWAY_DATE_ISO = datetime.strptime(RUNWAY_DATE, "%B %d, %Y %I:%M %p").isoformat()

# --- Payload for metadata parsing ---
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

# --- Payload for image analysis ---
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
                            "You are a fashion analyst. Analyze the image and return JSON with:\n"
                            "1) All visible clothing items, including small accessories (e.g. belts, scarves, gloves, leggings, boots).\n"
                            "2) For each item, estimate its main material (only one).\n"
                            "3) For each clothing item, estimate the dominant HEX color and its plain-text color name with no adjectives (e.g. '#FF0000' = 'red').\n\n"
                            "Return valid JSON in this format:\n"
                            "{\n"
                            "  \"clothing_items\": [...],\n"
                            "  \"material_decomposition\": { ... },\n"
                            "  \"item_colors_hex\": { \"jacket\": \"#FF0000\", ... },\n"
                            "  \"item_colors_name\": { \"jacket\": \"red\", ... }\n"
                            "}\n\n"
                            "Be precise. Only return JSON. Match keys between color and material dictionaries."
                        )
                    }
                ]
            }
        ]
    }

# --- Helper: Base64 encode image ---
def get_base64_image(bucket, key):
    response = s3.get_object(Bucket=bucket, Key=key)
    image_bytes = response['Body'].read()
    return base64.b64encode(image_bytes).decode("utf-8")

# --- Main pipeline ---
def analyze_and_upload():
    objects = s3.list_objects_v2(Bucket=bucket_name)
    images = [obj['Key'] for obj in objects.get('Contents', []) if obj['Key'].lower().endswith('.jpg')]

    print(f"🖼️ Found {len(images)} images in bucket")

    for key in images:
        try:
            print(f"\n🔍 Processing: {key}")
            filename = key.split("/")[-1]

            # Step 1: Metadata extraction
            meta_payload = create_metadata_payload(filename)
            meta_response = bedrock.invoke_model(
                modelId="anthropic.claude-3-haiku-20240307-v1:0",
                contentType="application/json",
                accept="application/json",
                body=json.dumps(meta_payload)
            )
            meta_result = json.loads(meta_response['body'].read())
            meta_text = meta_result["content"][0]["text"]
            try:
                meta = json.loads(meta_text)
            except json.JSONDecodeError:
                meta = ast.literal_eval(meta_text)

            # Step 2: Image analysis
            image_b64 = get_base64_image(bucket_name, key)
            analysis_payload = create_analysis_payload(image_b64)
            analysis_response = bedrock.invoke_model(
                modelId="anthropic.claude-3-haiku-20240307-v1:0",
                contentType="application/json",
                accept="application/json",
                body=json.dumps(analysis_payload)
            )
            analysis_result = json.loads(analysis_response['body'].read())
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

                entry = {
                    "image_id": image_id,
                    "original_image_name": filename,
                    "timestamp": timestamp,
                    "item_name": item,
                    "materials": materials.get(item, "unknown"),
                    "color_hex": colors_hex.get(item, "unknown"),
                    "color_name": colors_name.get(item, "unknown"),
                    "designer": meta.get("designer", "unknown"),
                    "collection": meta.get("collection", "unknown"),
                    "season": meta.get("season", "unknown"),
                    "event": meta.get("event", "unknown"),
                    "runway_date": RUNWAY_DATE_ISO
                }

                print(f"⬆️ Uploading: {image_id}")
                table.put_item(Item=entry)

        except Exception as e:
            print(f"❌ Error processing {key}: {str(e)}")

    print("\n✅ All images processed.")

# Run
if __name__ == "__main__":
    analyze_and_upload()
