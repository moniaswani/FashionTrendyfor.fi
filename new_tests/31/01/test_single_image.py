#!/usr/bin/env python3
"""
Test script to analyze a single image with improved prompt
"""

import json
import base64
import boto3
from io import BytesIO
from PIL import Image

# Initialize Bedrock
REGION = "eu-west-2"
bedrock = boto3.client("bedrock-runtime", region_name=REGION)

def preprocess_image(image_path):
    """Load and preprocess image"""
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        img.thumbnail((1024, 1024))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

def analyze_image(image_b64: str):
    """Analyze image with improved prompt"""
    payload = {
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
                        "text": """You are a highly precise fashion image parsing system with exceptional attention to detail.

TASK:
Identify EVERY distinct clothing or wearable item visible on the model.
You MUST perform a systematic scan of the model from HEAD to TOE.

MANDATORY SCAN ORDER (check each category):
1. HEAD: hats, headbands, hair accessories
2. NECK/CHEST: necklaces, chains, pendants, scarves, ties
3. UPPER BODY: jackets, coats, shirts, tops, vests, cardigans
4. ARMS: bracelets, watches, arm warmers, sleeves (if separate)
5. HANDS: gloves, rings
6. WAIST: belts, sashes, fanny packs
7. LOWER BODY: trousers, shorts, skirts, dresses, leggings
8. CARRIED ITEMS: bags, purses, handbags, clutches, backpacks
9. FEET: shoes, boots, sandals, socks (if visible and distinct)

DEFINITION OF ITEM:
- Any separate wearable or carried object counts as an item
- Examples: jacket, shirt, top, trousers, shorts, skirt, dress, boots, shoes, sandals, bag, belt, scarf, necklace, bracelet, hat
- If two items are visually separate, they MUST be listed separately
- Jewelry counts as items (necklace, bracelet, ring, earring)
- Even small accessories must be included

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
- Double-check you haven't missed shorts, jewelry, or accessories"""
                    }
                ]
            }
        ]
    }
    
    response = bedrock.invoke_model(
        modelId="anthropic.claude-3-haiku-20240307-v1:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload)
    )
    
    response_body = json.loads(response["body"].read())
    response_text = response_body["content"][0]["text"]
    
    # Clean potential markdown code blocks
    response_text = response_text.replace("```json", "").replace("```", "").strip()
    return json.loads(response_text)

# Test on the uploaded image
print("🔍 Testing improved prompt on image...")
print("=" * 60)

image_path = "/Users/moni_aswani/Downloads/fi/FashionTrendyfor.fi/new_tests/31/01/output_segmented/Lacoste-Ready-To-Wear-Spring-Summer-2026-Paris-Fashion-Week-Runway-012_segmented.png"
image_b64 = preprocess_image(image_path)

print("📸 Analyzing image with Claude via Bedrock...")
result = analyze_image(image_b64)

print("\n✅ RESULTS:")
print(json.dumps(result, indent=2))

print("\n📊 SUMMARY:")
print(f"Total items found: {len(result['clothing_items'])}")
print(f"Items: {', '.join(result['clothing_items'])}")

print("\n🎨 COLORS:")
for item in result['clothing_items']:
    color_name = result['item_colors_name'].get(item, 'unknown')
    color_hex = result['item_colors_hex'].get(item, 'unknown')
    print(f"  {item}: {color_name} ({color_hex})")

print("\n🧵 MATERIALS:")
for item in result['clothing_items']:
    material = result['material_decomposition'].get(item, 'unknown')
    print(f"  {item}: {material}")
