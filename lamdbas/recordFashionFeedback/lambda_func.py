import json
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb", region_name="eu-west-2")
table = dynamodb.Table("FashionFeedback")

VALID_FEEDBACK_TYPES = {"like", "dislike"}


def lambda_handler(event, context):
    http_method = event.get("httpMethod", "")

    if http_method == "OPTIONS":
        return _response(200, {})

    if http_method == "GET":
        return _handle_get(event)

    if http_method == "POST":
        return _handle_post(event)

    return _response(405, {"message": "Method not allowed"})


def _handle_get(event):
    params = event.get("queryStringParameters") or {}
    image_id = (params.get("image_id") or "").strip()
    if not image_id:
        return _response(400, {"message": "Missing image_id"})

    try:
        res = table.get_item(Key={"image_id": image_id})
        item = res.get("Item", {})
        return _response(200, {
            "image_id": image_id,
            "likes": int(item.get("likes", 0)),
            "dislikes": int(item.get("dislikes", 0)),
        })
    except ClientError as e:
        print("DynamoDB error:", e)
        return _response(500, {"message": "Internal error"})


def _handle_post(event):
    try:
        body = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return _response(400, {"message": "Invalid JSON body"})

    image_id = (body.get("image_id") or "").strip()
    feedback_type = (body.get("feedback_type") or "").strip().lower()

    if not image_id:
        return _response(400, {"message": "Missing image_id"})
    if feedback_type not in VALID_FEEDBACK_TYPES:
        return _response(400, {"message": "feedback_type must be 'like' or 'dislike'"})

    increment_field = feedback_type + "s"  # "likes" or "dislikes"
    try:
        res = table.update_item(
            Key={"image_id": image_id},
            UpdateExpression=(
                "SET #f = if_not_exists(#f, :zero) + :one, "
                "designer = if_not_exists(designer, :des), "
                "#season = if_not_exists(#season, :sea), "
                "original_image_name = if_not_exists(original_image_name, :oin)"
            ),
            ExpressionAttributeNames={
                "#f": increment_field,
                "#season": "season",
            },
            ExpressionAttributeValues={
                ":zero": 0,
                ":one": 1,
                ":des": body.get("designer", ""),
                ":sea": body.get("season", ""),
                ":oin": body.get("original_image_name", ""),
            },
            ReturnValues="ALL_NEW",
        )
        attrs = res.get("Attributes", {})
        return _response(200, {
            "image_id": image_id,
            "likes": int(attrs.get("likes", 0)),
            "dislikes": int(attrs.get("dislikes", 0)),
        })
    except ClientError as e:
        print("DynamoDB error:", e)
        return _response(500, {"message": "Internal error"})


def _response(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Content-Type": "application/json",
        },
        "body": json.dumps(body),
    }
