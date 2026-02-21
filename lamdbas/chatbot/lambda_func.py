import json
import boto3
from decimal import Decimal

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb", region_name="eu-west-2")
table = dynamodb.Table("FashionAnalysis")
bedrock = boto3.client("bedrock-runtime", region_name="eu-west-2")

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        question = body.get("question", "")

        # ✅ Scan the ENTIRE table (handle pagination)
        items = []
        scan_kwargs = {}
        while True:
            response = table.scan(**scan_kwargs)
            items.extend(response.get("Items", []))
            if "LastEvaluatedKey" not in response:
                break
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

        if not items:
            return {
                "statusCode": 200,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"answer": "No fashion data found in DynamoDB."}),
            }

        # ✅ Summarize relevant fields for Claude
        fashion_data = "\n".join([
            f"{i.get('designer', 'N/A')} - {i.get('item_name', 'N/A')} - {i.get('color_name', 'N/A')} - {i.get('materials', 'N/A')}"
            for i in items
        ])

        # ✅ Claude 3 prompt
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "You are a fashion AI analyst. You have access to runway collection data.\n\n"
                            f"Runway data:\n{fashion_data}\n\n"
                            f"User question: {question}\n\n"
                            "Think briefly about the data before responding. "
                            "Then answer in 1–3 short, direct sentences summarizing the insights. "
                            "If the data is unclear or irrelevant, say 'I'm not sure based on the available data.'"
                        ),
                    }
                ],
            }
        ]

        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": messages,
            "max_tokens": 350,
            "temperature": 0.5,
        }

        # ✅ Call Claude 3 Haiku on Bedrock
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            body=json.dumps(payload),
        )

        result = json.loads(response["body"].read().decode("utf-8"))

        # ✅ Extract text response
        answer = "".join(
            block.get("text", "")
            for block in result.get("content", [])
            if block.get("type") == "text"
        )

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
            "body": json.dumps({"answer": answer}),
        }

    except Exception as e:
        print("Error:", e)
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }
