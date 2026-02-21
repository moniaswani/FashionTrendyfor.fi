import boto3
from ultralytics import YOLO
from PIL import Image
from io import BytesIO
import os

# =====================
# CONFIG
# =====================
BUCKET = "runwayimages"
SOURCE_PREFIX = "balenciaga-ready-to-wear-spring-summer-2026-paris/"
OUTPUT_PREFIX = "balenciaga-ready-to-wear-spring-summer-2026-paris/cropped/"

CONF_THRESHOLD = 0.4

# Vertical splits (tuned for runway poses)
TOP_RATIO = 0.40
BOTTOM_RATIO = 0.75

# =====================
# INIT
# =====================
s3 = boto3.client("s3")
model = YOLO("yolov8s.pt")

# =====================
# HELPERS
# =====================
def list_images(bucket, prefix):
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

    return [
        obj["Key"]
        for page in pages
        for obj in page.get("Contents", [])
        if obj["Key"].lower().endswith((".jpg", ".jpeg", ".png"))
    ]


def load_image(bucket, key):
    obj = s3.get_object(Bucket=bucket, Key=key)
    return Image.open(BytesIO(obj["Body"].read())).convert("RGB")


def upload_crop(bucket, key, image):
    buf = BytesIO()
    image.save(buf, format="JPEG", quality=90)
    buf.seek(0)

    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=buf,
        ContentType="image/jpeg"
    )


def split_person(image, bbox):
    x1, y1, x2, y2 = bbox
    height = y2 - y1

    top_box = (
        x1,
        y1,
        x2,
        y1 + int(height * 0.45),
    )

    bottom_box = (
        x1,
        y1 + int(height * 0.35),
        x2,
        y1 + int(height * 0.85),
    )

    shoes_box = (
        x1,
        y1 + int(height * 0.75),
        x2,
        y2,
    )

    return {
        "top": image.crop(top_box),
        "bottom": image.crop(bottom_box),
        "shoes": image.crop(shoes_box),
    }


# =====================
# PIPELINE
# =====================
def process_image(s3_key):
    print(f"\n🔍 Processing: {s3_key}")
    image = load_image(BUCKET, s3_key)
    image_name = os.path.basename(s3_key).rsplit(".", 1)[0]

    results = model(image)[0]

    # Find the highest-confidence person
    person_boxes = [
        box for box in results.boxes
        if model.names[int(box.cls)] == "person"
        and float(box.conf) > CONF_THRESHOLD
    ]

    if not person_boxes:
        print("⚠️ No person detected")
        return

    # Use largest person box (runway model assumption)
    person_box = max(
        person_boxes,
        key=lambda b: (b.xyxy[0][2] - b.xyxy[0][0]) *
                      (b.xyxy[0][3] - b.xyxy[0][1])
    )

    x1, y1, x2, y2 = map(int, person_box.xyxy[0])
    crops = split_person(image, (x1, y1, x2, y2))

    for label, crop in crops.items():
        crop_key = (
            f"{OUTPUT_PREFIX}"
            f"{image_name}_{label}.jpg"
        )

        upload_crop(BUCKET, crop_key, crop)
        print(f"⬆️ Uploaded: {crop_key}")

# =====================
# MAIN
# =====================
def main():
    images = list_images(BUCKET, SOURCE_PREFIX)
    print(f"📸 Found {len(images)} images")

    for key in images:
        process_image(key)

    print("\n✅ Done: top / bottom / shoes baseline")


if __name__ == "__main__":
    main()