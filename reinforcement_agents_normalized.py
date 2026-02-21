"""
ITEM NORMALIZATION AND VALIDATION
Enforces single-word item names, removes hairstyles, and cleans data
"""

import json
from typing import Dict, List, Tuple


# ============== ITEM NORMALIZATION ==============

HAIRSTYLE_KEYWORDS = [
    "ponytail", "braid", "bun", "updo", "curly", "straight", "wavy",
    "slicked", "hair", "styled", "waves", "coils", "afro", "highlights",
    "layers", "bangs", "fringe", "shaved", "dyed", "bleached", "ombre",
    "balayage", "highlights", "roots", "texture"
]

VALID_ITEM_NAMES = {
    # Head
    "cap", "hat", "beanie", "headband", "crown", "tiara",
    
    # Jewelry/Accessories
    "earrings", "necklace", "bracelet", "ring", "anklet", "brooch",
    "pendant", "chain", "locket", "cufflinks",
    
    # Upper Body
    "shirt", "top", "blouse", "sweater", "cardigan", "tank",
    "vest", "jacket", "blazer", "coat", "trench", "parka",
    "hoodie", "sweatshirt", "pullover", "turtleneck", "crop",
    "bodice", "corset", "bodyssuit",
    
    # Lower Body
    "pants", "trousers", "jeans", "shorts", "skirt", "dress",
    "leggings", "tights", "culottes", "bermudas", "capris",
    
    # Feet
    "shoes", "boots", "sandals", "heels", "pumps", "flats",
    "sneakers", "loafers", "oxfords", "slippers", "mules", "clogs",
    
    # Accessories/Worn Items
    "belt", "scarf", "shawl", "wrap", "stole", "cape",
    "bag", "purse", "clutch", "backpack", "tote", "satchel",
    "gloves", "mittens", "socks",
    
    # Eyewear
    "glasses", "sunglasses", "goggles",
}

INVALID_ITEM_PATTERNS = [
    # Hairstyles
    "ponytail", "braid", "hair", "styled hair", "updo", "bun",
    # Multi-word descriptions
    "printed", "patterned", "lightweight", "floral", "polka",
    # Vague descriptions
    "outfit", "ensemble", "look", "style",
]


def is_hairstyle(item_name: str) -> bool:
    """Check if item is a hairstyle rather than clothing"""
    item_lower = item_name.lower()
    
    for keyword in HAIRSTYLE_KEYWORDS:
        if keyword in item_lower:
            return True
    
    return False


def normalize_item_name(item_name: str) -> str:
    """
    Convert multi-word items to single word
    
    Examples:
    "floral printed dress/tunic" → "dress"
    "small black clutch/purse" → "clutch"
    "sleek ponytail hairstyle" → FILTERED OUT
    """
    
    # Remove if hairstyle
    if is_hairstyle(item_name):
        return None
    
    item_lower = item_name.lower().strip()
    
    # Remove descriptors and get the core item
    # Pattern: remove adjectives, keep the noun
    
    # Remove forward slash variants (clutch/purse → clutch)
    if "/" in item_lower:
        items = item_lower.split("/")
        # Take the first one (usually most specific)
        item_lower = items[0].strip()
    
    # Extract single word from multi-word description
    words = item_lower.split()
    
    # If already single word and valid, return
    if len(words) == 1 and item_lower in VALID_ITEM_NAMES:
        return item_lower
    
    # Try to find the noun (last word usually)
    for word in reversed(words):
        if word in VALID_ITEM_NAMES:
            return word
    
    # Try to find any valid item word
    for word in words:
        if word in VALID_ITEM_NAMES:
            return word
    
    # If no valid item found, return None
    return None


def validate_material(item: str, material: str) -> Tuple[bool, str]:
    """
    Validate material makes sense for item type
    
    Returns: (is_valid, corrected_material)
    """
    
    material_lower = material.lower().strip()
    
    # Define valid materials for each item type
    material_rules = {
        "cap": ["wool", "cotton", "felt", "silk", "synthetic", "polyester"],
        "hat": ["wool", "cotton", "felt", "silk", "synthetic", "polyester"],
        "headband": ["cotton", "elastic", "metal", "synthetic"],
        "earrings": ["metal", "gold", "silver", "pearl", "glass", "plastic"],
        "necklace": ["metal", "gold", "silver", "pearl", "leather"],
        "bracelet": ["metal", "gold", "silver", "leather"],
        "ring": ["metal", "gold", "silver", "platinum"],
        "shirt": ["cotton", "silk", "linen", "polyester", "wool", "rayon"],
        "top": ["cotton", "silk", "linen", "polyester", "wool", "rayon"],
        "blouse": ["cotton", "silk", "linen", "polyester"],
        "sweater": ["wool", "cotton", "synthetic", "cashmere"],
        "cardigan": ["wool", "cotton", "synthetic", "cashmere"],
        "jacket": ["wool", "cotton", "silk", "leather", "polyester", "linen", "denim"],
        "blazer": ["wool", "cotton", "silk", "leather", "polyester"],
        "coat": ["wool", "cotton", "silk", "leather", "polyester", "nylon"],
        "pants": ["cotton", "wool", "linen", "polyester", "denim"],
        "trousers": ["cotton", "wool", "linen", "polyester", "denim"],
        "jeans": ["denim", "cotton"],
        "skirt": ["cotton", "wool", "silk", "polyester", "linen"],
        "dress": ["cotton", "wool", "silk", "polyester", "linen"],
        "leggings": ["cotton", "polyester", "spandex", "nylon"],
        "boots": ["leather", "suede", "rubber", "synthetic"],
        "shoes": ["leather", "suede", "canvas", "rubber", "synthetic"],
        "sandals": ["leather", "rubber", "EVA foam", "synthetic"],
        "heels": ["leather", "suede", "satin", "synthetic"],
        "belt": ["leather", "metal", "canvas", "synthetic"],
        "bag": ["leather", "canvas", "synthetic", "nylon", "suede"],
        "purse": ["leather", "canvas", "synthetic", "suede"],
        "clutch": ["leather", "canvas", "synthetic", "suede", "satin"],
        "backpack": ["leather", "canvas", "nylon", "synthetic"],
        "scarf": ["silk", "wool", "cotton", "linen", "synthetic"],
        "gloves": ["leather", "wool", "cotton", "synthetic"],
        "socks": ["cotton", "wool", "nylon", "polyester"],
        "glasses": ["metal", "plastic", "acetate"],
    }
    
    valid_materials = material_rules.get(item, [])
    
    if not valid_materials:
        # Item not in rules, accept any reasonable material
        return True, material_lower
    
    # Check if material matches any valid option
    for valid_mat in valid_materials:
        if valid_mat.lower() in material_lower or material_lower in valid_mat.lower():
            return True, valid_mat.lower()
    
    # Not a valid material, suggest the first valid one
    return False, valid_materials[0] if valid_materials else "unknown"


def validate_and_normalize_extraction(analysis_json: Dict) -> Dict:
    """
    Validate and normalize extraction to enforce:
    - Single-word item names
    - No hairstyles
    - Valid materials
    - Proper color format
    
    Returns normalized JSON or raises error
    """
    
    items = analysis_json.get("clothing_items", [])
    materials = analysis_json.get("material_decomposition", {})
    colors_hex = analysis_json.get("item_colors_hex", {})
    colors_name = analysis_json.get("item_colors_name", {})
    
    normalized_items = []
    normalized_materials = {}
    normalized_hex = {}
    normalized_names = {}
    
    issues = []
    
    for item in items:
        # Step 1: Normalize item name
        normalized = normalize_item_name(item)
        
        if normalized is None:
            issues.append(f"❌ REMOVED: '{item}' - invalid item (hairstyle or non-clothing)")
            continue
        
        if normalized in normalized_items:
            issues.append(f"⚠️  SKIPPED: '{item}' normalizes to '{normalized}' (duplicate)")
            continue
        
        # Step 2: Validate and correct material
        material = materials.get(item, "unknown")
        is_valid_material, corrected_material = validate_material(normalized, material)
        
        if not is_valid_material:
            issues.append(f"⚠️  CORRECTED: '{item}' material from '{material}' to '{corrected_material}'")
        
        # Step 3: Validate color hex
        hex_color = colors_hex.get(item, "#000000")
        if not hex_color.startswith("#") or len(hex_color) != 7:
            issues.append(f"⚠️  INVALID COLOR HEX: '{item}' has '{hex_color}', using #000000")
            hex_color = "#000000"
        
        # Step 4: Validate color name
        color_name = colors_name.get(item, "unknown")
        if not color_name or color_name.lower() in ["unknown", ""]:
            color_name = "unknown"
        
        # Step 5: Add to normalized collections
        normalized_items.append(normalized)
        normalized_materials[normalized] = corrected_material
        normalized_hex[normalized] = hex_color
        normalized_names[normalized] = color_name
    
    # Validate coverage
    if len(normalized_items) < 6:
        issues.append(f"⚠️  LOW ITEM COUNT: Only {len(normalized_items)} items (should be 6+)")
    
    if len(normalized_items) == 0:
        raise ValueError("No valid items found after normalization")
    
    # Return normalized JSON
    normalized_json = {
        "clothing_items": normalized_items,
        "material_decomposition": normalized_materials,
        "item_colors_hex": normalized_hex,
        "item_colors_name": normalized_names,
        "normalization_issues": issues
    }
    
    return normalized_json


# ============== VALIDATION WITH NORMALIZATION ==============

def validate_extraction_strict(analysis_json: Dict) -> Dict:
    """
    Strict validation after normalization
    
    Returns:
    {
        "is_valid": True/False,
        "score": 0-100,
        "issues": [],
        "normalized": {...}
    }
    """
    
    try:
        # First normalize
        normalized = validate_and_normalize_extraction(analysis_json)
        
        items = normalized.get("clothing_items", [])
        normalization_issues = normalized.get("normalization_issues", [])
        
        # Now validate
        score = 100
        issues = []
        
        # Add normalization issues
        issues.extend(normalization_issues)
        score -= len(normalization_issues) * 5
        
        # Check item count
        if len(items) < 6:
            issues.append(f"Only {len(items)} valid items (need 6+)")
            score -= 20
        
        # Check all items have all fields
        materials = normalized.get("material_decomposition", {})
        hex_colors = normalized.get("item_colors_hex", {})
        color_names = normalized.get("item_colors_name", {})
        
        for item in items:
            if item not in materials:
                issues.append(f"{item}: missing material")
                score -= 5
            if item not in hex_colors:
                issues.append(f"{item}: missing hex color")
                score -= 5
            if item not in color_names:
                issues.append(f"{item}: missing color name")
                score -= 5
        
        is_valid = len(issues) == 0 and len(items) >= 6
        
        return {
            "is_valid": is_valid,
            "score": max(0, score),
            "issues": issues,
            "normalized": normalized
        }
        
    except Exception as e:
        return {
            "is_valid": False,
            "score": 0,
            "issues": [f"Normalization failed: {str(e)}"],
            "normalized": None
        }


# ============== USAGE ==============

"""
In your pipeline:

from reinforcement_agents_normalized import validate_extraction_strict

# After analyze_image returns JSON:
validation = validate_extraction_strict(analysis)

if validation["is_valid"]:
    # Use normalized version
    analysis = validation["normalized"]
    items = analysis["clothing_items"]
    
    for item in items:
        row = {
            "item_name": item,  # NOW SINGLE WORD
            "materials": analysis["material_decomposition"][item],
            "color_hex": analysis["item_colors_hex"][item],
            "color_name": analysis["item_colors_name"][item],
            ...
        }
        batch.put_item(Item=row)
else:
    print(f"Validation failed: {validation['issues']}")
"""
