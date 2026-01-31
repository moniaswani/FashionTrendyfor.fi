#!/usr/bin/env python3
"""
Local Fashion Analysis Script - AWS Bedrock Version
Analyzes runway images using AWS Bedrock Claude and saves results to CSV
"""

import os
import json
import base64
import csv
import boto3
from pathlib import Path
from datetime import datetime
from io import BytesIO
from PIL import Image

# ---------------- CONFIG ----------------
REGION = "eu-west-2"  # Same as your original script
RUNWAY_DATE = "October 6, 2025 2:00 pm"
RUNWAY_DATE_ISO = datetime.strptime(
    RUNWAY_DATE, "%B %d, %Y %I:%M %p"
).isoformat()

# Initialize Bedrock client
bedrock = boto3.client("bedrock-runtime", region_name=REGION)
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table("New_Fashion_Analysis")

# ---------------- HELPERS ----------------
def preprocess_image(image_path):
    """Load and preprocess image for Claude API"""
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            img.thumbnail((1024, 1024))
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=85)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"⚠️ Image preprocessing failed for {image_path}: {e}")
        return None


def extract_metadata(filename: str):
    """Extract metadata from filename using Claude via Bedrock"""
    payload = {
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
    
    try:
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )
        
        response_body = json.loads(response["body"].read())
        response_text = response_body["content"][0]["text"]
        
        # Clean potential markdown code blocks
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        return json.loads(response_text)
    except Exception as e:
        print(f"⚠️ Metadata extraction failed: {e}")
        return {
            "designer": "unknown",
            "collection": "unknown",
            "season": "unknown",
            "event": "unknown"
        }


def analyze_image(image_b64: str):
    """Analyze image using Claude Vision via Bedrock"""
    payload = {
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
                        "text": """You are a highly precise fashion image parsing system with exceptional attention to detail.

TASK:
BE AS ACCURATE AS POSSIBLE. Identify EVERY distinct clothing or wearable item visible on the model.
You MUST perform a systematic scan of the model from HEAD to TOE.

MANDATORY SCAN ORDER (check each category):
1. HEAD: hats, headbands, hair accessories
2. NECK/CHEST: necklaces, chains, pendants, scarves, ties
3. UPPER BODY LAYERS (check for ALL layers, from outer to inner):
   - Outer: coats, trench coats, overcoats, capes
   - Middle: jackets, blazers, cardigans, overshirts
   - Inner: shirts, tops, blouses, vests, tank tops, bodysuits
   - IMPORTANT: If you see multiple layers, list each one separately!
4. ARMS: bracelets, watches, arm warmers, sleeves (if separate)
5. HANDS & HELD ITEMS: 
   - On hands: gloves, rings
   - Held in hands: clutches, small bags, phones, folders, books
   - IMPORTANT: Look carefully at what the model is holding or carrying in their hands!
6. WAIST: belts, sashes, fanny packs
7. LOWER BODY: trousers, shorts, skirts, dresses, leggings
8. CARRIED ITEMS (on body): bags, purses, handbags, backpacks, crossbody bags
9. FEET: shoes, boots, sandals, slippers, socks (if visible and distinct)

DEFINITION OF ITEM:
- Any separate wearable or carried object counts as an item
- Examples: jacket, shirt, top, trousers, shorts, skirt, dress, boots, shoes, sandals, bag, belt, scarf, necklace, bracelet, hat, clutch
- If two items are visually separate, they MUST be listed separately
- Jewelry counts as items (necklace, bracelet, ring, earring)
- Even small accessories must be included
- LAYERING: If wearing coat over blazer over shirt, that's 3 separate items
- HANDHELD: If holding a clutch or small bag in hand, that's an item (separate from worn bags)

STRICT RULES:
- Each item name MUST be a single lowercase noun (no adjectives)
- No combined items (❌ 'jacket-and-shirt', ❌ 'crop-top')
- Each item MUST have exactly one material and one color
- Color names MUST be one word (e.g. 'black', 'white', 'orange', 'coral', 'burgundy', 'navy')
- Hex color MUST accurately represent the ACTUAL visible color you see
  * Look closely at the true color - is it really pure orange (#FF6600) or more coral (#FF7F50)?
  * Is it pure red (#FF0000) or more burgundy (#800020)?
  * Sample the dominant color you actually see in the image

COLOR ACCURACY:
- Before assigning colors, look CAREFULLY at the actual hue in the image
- Common colors: white (#FFFFFF), black (#000000), red (#FF0000), orange (#FF6600), 
  coral (#FF7F50), burgundy (#800020), navy (#000080), beige (#F5F5DC), cream (#FFFDD0)
- When in doubt between similar colors, choose the one that matches the visual better

COMPLETENESS CHECK:
- Before answering, verify you've checked ALL 9 categories above
- Count the items you found - does it seem complete?
- Look again for small accessories, jewelry, or partially hidden items
- If you see ANY jewelry (necklaces, bracelets, rings), you MUST include them
- LAYERING CHECK: Are there multiple upper body layers? (coat over blazer over shirt?)
  * If yes, make sure you've listed EACH layer as a separate item
  * Common mistake: Only listing the outer coat and missing the blazer/jacket underneath
- HANDHELD CHECK: Is the model holding anything in their hands?
  * Clutches, small bags, phones, folders - these count as items!
  * Look carefully at both hands

RETURN EXACTLY THIS JSON FORMAT:
{
  "clothing_items": ["item1", "item2", "item3"],
  "material_decomposition": {
    "item1": "material",
    "item2": "material"
  },
  "item_colors_hex": {
    "item1": "#RRGGBB",
    "item2": "#RRGGBB"
  },
  "item_colors_name": {
    "item1": "color",
    "item2": "color"
  }
}

IMPORTANT:
- All keys must be lowercase
- Every item in clothing_items MUST appear in ALL three mappings
- Output ONLY valid JSON
- No commentary, no markdown, no extra text
- Double-check you haven't missed shorts, jewelry, or accessories
- CRITICAL: Check for layering (coat + blazer + top = 3 items, not 1!)
- CRITICAL: Check both hands for clutches or small bags being held"""
                    }
                ]
            }
        ]
    }
    
    try:
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )
        
        response_body = json.loads(response["body"].read())
        response_text = response_body["content"][0]["text"]
        
        # Clean potential markdown code blocks
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        return json.loads(response_text)
    except Exception as e:
        print(f"⚠️ Image analysis failed: {e}")
        return {
            "clothing_items": [],
            "material_decomposition": {},
            "item_colors_hex": {},
            "item_colors_name": {}
        }


def check_if_processed(filename: str) -> bool:
    """Check if any item for this image already exists in DynamoDB"""
    try:
        response = table.query(
            IndexName="original_image_name-index",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("original_image_name").eq(filename)
        )
        return len(response.get("Items", [])) > 0
    except:
        return False



# ---------------- MAIN PIPELINE ----------------
def process_images(input_folder: str):
    """
    Process all images in input folder and save results to DynamoDB (New_Fashion_Analysis)
    """
    input_path = Path(input_folder)
    
    if not input_path.exists():
        print(f"❌ Error: Input folder '{input_folder}' does not exist")
        return
    
    # Get all image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
    image_files = [
        f for f in input_path.iterdir()
        if f.is_file() and f.suffix.lower() in image_extensions
    ]
    
    if not image_files:
        print(f"❌ No images found in {input_folder}")
        return
    
    print(f"📸 Found {len(image_files)} images to process")
    
    # Global batch writer
    with table.batch_writer() as batch:
        
        # Process each image
        for idx, image_file in enumerate(image_files, 1):
            filename = image_file.name
            
            # Clean filename
            original_filename = filename
            if '_segmented' in filename:
                base_name = filename.rsplit('_segmented', 1)[0]
                original_filename = f"{base_name}.jpg"
            
            print(f"\n🔍 [{idx}/{len(image_files)}] Processing: {filename}")
            
            try:
                # Extract metadata
                print(f"   📋 Extracting metadata...")
                metadata = extract_metadata(original_filename)
                
                # Preprocess image
                print(f"   🖼️  Preprocessing image...")
                image_b64 = preprocess_image(image_file)
                if not image_b64:
                    print(f"   ❌ Failed to preprocess image")
                    continue
                
                # Analyze image
                print(f"   🤖 Analyzing image with Claude (via Bedrock)...")
                analysis = analyze_image(image_b64)
                
                timestamp = datetime.utcnow().isoformat()
                
                items_found = analysis.get("clothing_items", [])
                print(f"   ✅ Found {len(items_found)} clothing items")
                
                for item in items_found:
                    image_id = f"{original_filename}_{item}".lower()
                    
                    row = {
                        'image_id': image_id,
                        'original_image_name': original_filename,
                        'timestamp': timestamp,
                        'item_name': item,
                        'materials': analysis["material_decomposition"].get(item, "unknown"),
                        'color_hex': analysis["item_colors_hex"].get(item, "unknown"),
                        'color_name': analysis["item_colors_name"].get(item, "unknown"),
                        'designer': metadata.get("designer", "unknown"),
                        'collection': metadata.get("collection", "unknown"),
                        'season': metadata.get("season", "unknown"),
                        'event': metadata.get("event", "unknown"),
                        'runway_date': RUNWAY_DATE_ISO,
                    }
                    
                    batch.put_item(Item=row)
                    print(f"   ⬆️  Inserted: {image_id}")
                
            except Exception as e:
                print(f"   ❌ Error processing {original_filename}: {e}")
                continue
    
    print(f"\n✅ PROCESSING COMPLETE!")
    print(f"📦 Results saved to DynamoDB table: New_Fashion_Analysis")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Analyze runway fashion images using AWS Bedrock and save results to DynamoDB"
    )
    parser.add_argument(
        "input_folder",
        help="Path to folder containing runway images"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("FASHION IMAGE ANALYSIS - AWS BEDROCK VERSION")
    print("=" * 60)
    print(f"Input folder: {args.input_folder}")
    print(f"AWS Region: {REGION}")
    print(f"DynamoDB Table: New_Fashion_Analysis")
    print("=" * 60)
    
    process_images(args.input_folder)


if __name__ == "__main__":
    main()
