#!/usr/bin/env python3
"""
Local Fashion Analysis Script - AWS Bedrock Version
Optimized version that loads existing filenames into memory for fast checking
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
from boto3.dynamodb.conditions import Attr
import boto3


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

# ===== Statistics tracking =====
stats = {
    "total_found": 0,
    "skipped": 0,
    "processed": 0,
    "total_items_inserted": 0,
}

# ===== Cache for existing filenames =====
existing_filenames = set()

# ---------------- HELPERS ----------------
def load_existing_filenames():
    """
    Load all existing original_image_name values from DynamoDB into memory
    This is much faster than scanning for each individual file
    """
    global existing_filenames
    
    print("📥 Loading existing filenames from DynamoDB...")
    existing_filenames = set()
    
    try:
        # Scan all items and collect unique original_image_name values
        scan_kwargs = {
            'ProjectionExpression': 'original_image_name'
        }
        
        done = False
        start_key = None
        count = 0
        
        while not done:
            if start_key:
                scan_kwargs['ExclusiveStartKey'] = start_key
            
            response = table.scan(**scan_kwargs)
            
            # Add all filenames to set (automatically deduplicates)
            for item in response.get('Items', []):
                filename = item.get('original_image_name')
                if filename:
                    existing_filenames.add(filename)
                    count += 1
            
            # Check if there are more items
            start_key = response.get('LastEvaluatedKey')
            done = not start_key
        
        print(f"✅ Loaded {len(existing_filenames)} unique filenames from DynamoDB\n")
        
    except Exception as e:
        print(f"⚠️ Failed to load filenames: {e}")
        print("   Continuing without caching (will be slower)\n")


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


def format_for_dynamodb(filename: str) -> str:
    """
    Convert filename to match DynamoDB format
    Example: "miu-miu-ready-to-wear-fall-winter-2018-fashion-show-runway-0003.jpg"
    Becomes: "Miu-Miu-Ready-To-Wear-Fall-Winter-2018-Fashion-Show-Runway-0003.jpg"
    """
    # Remove .jpg extension
    name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
    
    # Split by hyphen and capitalize each word
    words = name_without_ext.split('-')
    capitalized = [word.capitalize() for word in words]
    
    # Rejoin and add .jpg
    return '-'.join(capitalized) + '.jpg'


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
    """Analyze image using Claude Vision via Bedrock - TWO STAGE APPROACH"""
    
    # STAGE 1: Describe what's in the image
    stage1_payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 800,
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
                        "text": """Carefully describe this runway fashion image. Be very specific about what you observe:

1. HEAD: What is on the model's head? (hat, cap, headband, etc.)
2. FACE/EARS: Are there earrings or other jewelry visible on the face/ears?
3. NECK/CHEST: Any necklaces, scarves, or chest jewelry?
4. UPPER BODY: What garments are worn on the torso? 
   - Describe from outside to inside (outer jacket/coat first, then layers underneath)
   - Are there multiple distinct layers?
5. WAIST: Is there a belt or waist accessory? What color?
6. HANDS: What is the model holding in their hands? (bags, clutches, phones, etc.)
7. LOWER BODY: What is worn on legs? (pants, skirt, shorts, etc.)
8. FEET: What footwear is visible? (shoes, boots, sandals, etc.)

Be as detailed and accurate as possible. This description will be used to ensure complete item detection.

Return ONLY a text description, no JSON, no markdown."""
                    }
                ]
            }
        ]
    }
    
    try:
        # Get stage 1 response
        response1 = bedrock.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(stage1_payload)
        )
        
        response1_body = json.loads(response1["body"].read())
        outfit_description = response1_body["content"][0]["text"]
        
        print(f"   📝 Outfit description:\n{outfit_description}\n")
        
    except Exception as e:
        print(f"⚠️ Stage 1 (description) failed: {e}")
        outfit_description = ""
    
    # STAGE 2: Extract items based on the description
    stage2_payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1500,
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
                        "text": f"""You are a complete fashion item detection system. Based on the outfit description below, extract EVERY item visible.

OUTFIT DESCRIPTION (from detailed analysis):
{outfit_description}

---

YOUR TASK: Extract all items mentioned or implied in the description above. Do not miss anything.

CRITICAL RULES - AVOID DUPLICATES:
1. Every item mentioned in the description MUST be in your output
2. Each item gets ONE entry in clothing_items (no duplicates, no combining)
3. Every item must have material and color assignments
4. Count items: you should have 6-10 items for a complete runway outfit
5. ITEM NAMES MUST BE SINGLE WORDS (no spaces, no slashes)
6. Do NOT include hairstyles as items

EXCLUSIVITY RULES (PREVENT DOUBLE-COUNTING):
❌ NEVER include BOTH:
- "dress" AND "skirt" (dress IS the skirt, count dress ONLY)
- "pants" AND "trousers" (same item, pick one)
- "overcoat" AND "coat" (pick the more visible one)

✅ DO include both ONLY if clearly separate:
- "blazer" + "shirt" (different layers, include both)
- "overcoat" + "jacket" + "shirt" (3 distinct layers, include all)
- "belt" + "pants" (different items, include both)

ITEM SELECTION FOR LOWER BODY:
- If it's a DRESS: choose "dress" (not "skirt")
- If it's PANTS: choose "pants" (not "trousers")
- If it's a SKIRT: choose "skirt" (not "dress")
- If BOTH pants AND skirt visible: include both (unlikely but possible)

LAYERING RULE:
If description mentions multiple DISTINCT upper body layers:
- Outer layer: list as separate item
- Middle layer: list as separate item (if visually distinct)
- Inner layer: list as separate item (if visually distinct/visible)
Example: "overcoat over jacket over shirt" = 3 items ✅
Example: "dress" = 1 item (not dress + skirt) ✅

HANDHELD RULE:
If description says model is holding something:
- Bag in hand: include as "bag" or specific type
- Clutch in hand: include as "clutch"
- Any carried item: include in clothing_items

VALID ITEM NAMES (single word only):
cap, hat, headband, earrings, necklace, bracelet, ring, shirt, top, blouse, 
sweater, jacket, blazer, coat, overcoat, pants, trousers, skirt, dress, belt, bag, 
shoes, boots, sandals, gloves, scarf, glasses

MATERIAL ASSIGNMENT (based on visual appearance and item type):
- Caps/hats: wool, cotton, felt, silk, synthetic
- Jewelry: metal, gold, silver, platinum, pearl, glass
- Shirts/tops: cotton, silk, linen, polyester, wool
- Jackets/coats: wool, cotton, silk, leather, polyester, nylon
- Pants/trousers: cotton, wool, linen, polyester, denim
- Belts: leather, metal, canvas, synthetic
- Bags: leather, canvas, synthetic, nylon, suede
- Shoes: leather, suede, canvas, rubber, synthetic, EVA foam

COLOR ACCURACY:
Assign colors based on what you actually see:
- Black: #000000
- White: #FFFFFF
- Gold/metallic: #FFD700
- Silver/metallic: #C0C0C0
- Brown: #8B4513
- Navy: #000080
- Beige: #F5F5DC
- Cream: #FFFDD0

COMPLETENESS VERIFICATION:
Before outputting JSON, verify:
☐ Did I avoid "dress" AND "skirt" (choose one)?
☐ Did I avoid "pants" AND "trousers" (choose one)?
☐ Did I list each DISTINCT upper body layer separately?
☐ Did I include handheld items the model is holding?
☐ Did I include jewelry (earrings, necklaces, etc.)?
☐ Did I include footwear?
☐ Did I include belt if mentioned?
☐ Total item count: 6-10 items (runway outfit standard)
☐ Every item appears in all 3 mappings (materials, hex colors, color names)

RETURN ONLY VALID JSON:
{{
  "clothing_items": ["item1", "item2", "item3"],
  "material_decomposition": {{
    "item1": "material",
    "item2": "material"
  }},
  "item_colors_hex": {{
    "item1": "#RRGGBB",
    "item2": "#RRGGBB"
  }},
  "item_colors_name": {{
    "item1": "color",
    "item2": "color"
  }}
}}

NO MARKDOWN, NO COMMENTARY, ONLY JSON."""
                    }
                ]
            }
        ]
    }
    
    try:
        # Get stage 2 response
        response2 = bedrock.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(stage2_payload)
        )
        
        response2_body = json.loads(response2["body"].read())
        response_text = response2_body["content"][0]["text"]
        
        # Clean potential markdown code blocks
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        return json.loads(response_text)
        
    except Exception as e:
        print(f"⚠️ Stage 2 (extraction) failed: {e}")
        return {
            "clothing_items": [],
            "material_decomposition": {},
            "item_colors_hex": {},
            "item_colors_name": {}
        }


def check_if_processed(filename: str) -> bool:
    """Check if filename exists in cached set"""
    is_processed = filename in existing_filenames
    status = "✅ EXISTS in DynamoDB" if is_processed else "❌ NOT in DynamoDB (new)"
    print(f"   📝 Original name: {filename} | {status}")
    return is_processed


# ---------------- MAIN PIPELINE ----------------

def process_images(input_folder: str):
    """
    Recursively process all images in input folder and subfolders,
    saving results to DynamoDB (New_Fashion_Analysis) and skipping
    images already processed.
    """
    # Load existing filenames first
    load_existing_filenames()
    
    input_path = Path(input_folder)
    if not input_path.exists():
        print(f"❌ Error: Input folder '{input_folder}' does not exist")
        return

    # Supported image formats
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}

    # Recursively get all image files
    image_files = [
        f for f in input_path.rglob("*")
        if f.is_file() and f.suffix.lower() in image_extensions
    ]

    if not image_files:
        print(f"❌ No images found in {input_folder}")
        return

    stats["total_found"] = len(image_files)
    print(f"📸 Found {len(image_files)} images to process (recursive)\n")

    # Global batch writer
    with table.batch_writer() as batch:
        for idx, image_file in enumerate(image_files, 1):
            # Get original filename from file
            original_filename = image_file.name
            
            # Handle _segmented files - remove _segmented suffix
            if '_segmented' in original_filename:
                base_name = original_filename.rsplit('_segmented', 1)[0]
                original_filename = f"{base_name}.jpg"
            
            # Format filename to match DynamoDB format (Proper-Case-With-Dashes.jpg)
            db_original_name = format_for_dynamodb(original_filename)

            # Check if already processed (instant lookup from cache)
            if check_if_processed(db_original_name):
                print(f"   ⏭️  SKIPPED (already processed)")
                stats["skipped"] += 1
                continue

            print(f"\n🔍 [{idx}/{len(image_files)}] Processing: {original_filename}")
            stats["processed"] += 1

            try:
                # Extract metadata
                print(f"   📋 Extracting metadata...")
                metadata = extract_metadata(db_original_name)

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

                # Insert each item into DynamoDB
                for item in items_found:
                    image_id = f"{db_original_name}_{item}".lower()
                    row = {
                        'image_id': image_id,
                        'original_image_name': db_original_name,
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
                    stats["total_items_inserted"] += 1

            except Exception as e:
                print(f"   ❌ Error processing {original_filename}: {e}")
                continue

    # Print statistics
    print(f"\n" + "="*60)
    print(f"✅ PROCESSING COMPLETE!")
    print(f"="*60)
    print(f"📊 STATISTICS:")
    print(f"   Total found: {stats['total_found']} images")
    print(f"   ⏭️  Skipped: {stats['skipped']} images (already processed)")
    print(f"   Processed: {stats['processed']} new images")
    print(f"   📦 Total items inserted: {stats['total_items_inserted']}")
    
    print(f"\n📦 Results saved to DynamoDB table: New_Fashion_Analysis")


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
    print("=" * 60 + "\n")
    
    process_images(args.input_folder)


if __name__ == "__main__":
    main()