"""
Local test runner for chatbot lambda_func.py
Run: python test_local.py
Requires AWS credentials with access to DynamoDB (eu-west-2) and Bedrock.
"""
import json
from lambda_func import lambda_handler

def invoke(question: str, history: list = []):
    event = {
        "httpMethod": "POST",
        "body": json.dumps({"question": question, "history": history}),
    }
    result = lambda_handler(event, None)
    body = json.loads(result["body"])
    print(f"\n{'='*60}")
    print(f"Q: {question}")
    print(f"Status: {result['statusCode']}")
    print(f"Answer:\n{body.get('answer', body.get('error', ''))}")
    images = body.get("images", [])
    if images:
        print(f"Images ({len(images)}):")
        for url in images:
            print(f"  {url}")
    return body


if __name__ == "__main__":
    # Test 1: Q&A with a collection that has articles scraped
    invoke("What can you tell me about the Maison Margiela Spring 2026 collection?")

    # Test 2: Scrape command
    # invoke("scrape this article: https://www.vogue.com/fashion-shows/spring-2026-ready-to-wear/maison-martin-margiela")

    # Test 3: Collection without runway data (tests S3 fallback)
    # invoke("Tell me about Miu Miu Fall 2025")
