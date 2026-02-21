import json
import base64
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb", region_name="eu-west-2")
table = dynamodb.Table("New_Fashion_Analysis")

MAX_LIMIT = 500
DEFAULT_LIMIT = 200


def parse_multi(params, key):
    """Parse a comma-separated query param into a list of lowercase strings."""
    raw = params.get(key, "").strip()
    return [v.strip().lower() for v in raw.split(",") if v.strip()] if raw else []


def build_or_filter(field, values, prefix):
    """
    Build a DynamoDB FilterExpression fragment for OR contains across multiple values.
    Returns (expression_str, attr_values_dict).
    """
    conditions = []
    attr_values = {}
    for i, v in enumerate(values):
        k = f":{prefix}{i}"
        attr_values[k] = v
        conditions.append(f"contains({field}, {k})")
    expr = f"({' OR '.join(conditions)})"
    return expr, attr_values


def lambda_handler(event, context):
    try:
        params = event.get("queryStringParameters") or {}

        designers = parse_multi(params, "designer")
        seasons   = parse_multi(params, "season")
        colors    = parse_multi(params, "color_name")
        item_names = parse_multi(params, "item_name")
        materials  = parse_multi(params, "materials")
        next_token = params.get("next_token", "").strip()

        try:
            limit = min(int(params.get("limit", DEFAULT_LIMIT)), MAX_LIMIT)
        except (ValueError, TypeError):
            limit = DEFAULT_LIMIT

        if not any([designers, seasons, colors, item_names, materials]):
            return response(400, {"error": "At least one filter is required"})

        # Build FilterExpression parts for color / item / material (always OR-across-values)
        filter_parts = []
        expr_attr_values = {}

        if colors:
            expr, vals = build_or_filter("color_name", colors, "color")
            filter_parts.append(expr)
            expr_attr_values.update(vals)

        if item_names:
            expr, vals = build_or_filter("item_name", item_names, "item")
            filter_parts.append(expr)
            expr_attr_values.update(vals)

        if materials:
            expr, vals = build_or_filter("materials", materials, "mat")
            filter_parts.append(expr)
            expr_attr_values.update(vals)

        # Decode pagination cursor
        exclusive_start_key = None
        if next_token:
            try:
                exclusive_start_key = json.loads(base64.b64decode(next_token).decode("utf-8"))
            except Exception:
                return response(400, {"error": "Invalid next_token"})

        items = []
        last_evaluated_key = None

        # Route: single designer + single season → GSI (most efficient)
        if len(designers) == 1 and len(seasons) == 1:
            query_kwargs = {
                "IndexName": "DesignerSeasonIndex",
                "KeyConditionExpression": (
                    Key("designer_lower").eq(designers[0]) &
                    Key("season_lower").eq(seasons[0])
                ),
            }
            if filter_parts:
                query_kwargs["FilterExpression"] = " AND ".join(filter_parts)
                query_kwargs["ExpressionAttributeValues"] = expr_attr_values
            if exclusive_start_key:
                query_kwargs["ExclusiveStartKey"] = exclusive_start_key

            while len(items) < limit:
                res = table.query(**query_kwargs)
                items.extend(res.get("Items", []))
                last_evaluated_key = res.get("LastEvaluatedKey")
                if not last_evaluated_key or len(items) >= limit:
                    break
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

        elif len(designers) == 1 and len(seasons) == 0:
            # GSI PK only — all seasons for one designer
            query_kwargs = {
                "IndexName": "DesignerSeasonIndex",
                "KeyConditionExpression": Key("designer_lower").eq(designers[0]),
            }
            if filter_parts:
                query_kwargs["FilterExpression"] = " AND ".join(filter_parts)
                query_kwargs["ExpressionAttributeValues"] = expr_attr_values
            if exclusive_start_key:
                query_kwargs["ExclusiveStartKey"] = exclusive_start_key

            while len(items) < limit:
                res = table.query(**query_kwargs)
                items.extend(res.get("Items", []))
                last_evaluated_key = res.get("LastEvaluatedKey")
                if not last_evaluated_key or len(items) >= limit:
                    break
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

        else:
            # Scan path — multiple designers, multiple seasons, or season-only
            scan_filter_parts = list(filter_parts)
            scan_expr_values = dict(expr_attr_values)

            if designers:
                expr, vals = build_or_filter("designer_lower", designers, "des")
                scan_filter_parts.append(expr)
                scan_expr_values.update(vals)

            if seasons:
                expr, vals = build_or_filter("season_lower", seasons, "sea")
                scan_filter_parts.append(expr)
                scan_expr_values.update(vals)

            scan_kwargs = {}
            if scan_filter_parts:
                scan_kwargs["FilterExpression"] = " AND ".join(scan_filter_parts)
                scan_kwargs["ExpressionAttributeValues"] = scan_expr_values
            if exclusive_start_key:
                scan_kwargs["ExclusiveStartKey"] = exclusive_start_key

            while len(items) < limit:
                res = table.scan(**scan_kwargs)
                items.extend(res.get("Items", []))
                last_evaluated_key = res.get("LastEvaluatedKey")
                if not last_evaluated_key or len(items) >= limit:
                    break
                scan_kwargs["ExclusiveStartKey"] = last_evaluated_key

        result_items = items[:limit]
        encoded_next_token = None

        if last_evaluated_key and (len(items) >= limit or len(items) == limit):
            encoded_next_token = base64.b64encode(
                json.dumps(last_evaluated_key, default=str).encode("utf-8")
            ).decode("utf-8")

        return response(200, {
            "items": result_items,
            "next_token": encoded_next_token,
            "count": len(result_items),
        })

    except Exception as e:
        print("ERROR:", str(e))
        return response(500, {"error": str(e)})


def response(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Content-Type": "application/json",
        },
        "body": json.dumps(body, default=str),
    }
