"""
Conversational chatbot over the fashion agent's InsightsCache.

Usage:
    python chat.py

Ask questions like:
    "Tell me about Chanel spring 2023"
    "What were the key colors for Louis Vuitton fall 2023?"
    "How did critics feel about Balenciaga last season?"

The bot extracts designer/season from your question, fetches insights
(running the full pipeline if not yet cached), then answers conversationally.
"""

import json
import os

import boto3

from analyst import CLAUDE_MODEL, REGION, analyze
from dynamo_client import get_cached_insights

_bedrock = boto3.client("bedrock-runtime", region_name=REGION)

_SYSTEM = """You are a fashion intelligence assistant. You have access to structured analysis
combining editorial reviews (Vogue, WWD, and other publications) with computer vision data
from runway photographs.

When given insights data, answer questions conversationally and specifically — reference
actual themes, colors, materials, and tensions from the data. Keep answers concise (3-5 sentences
unless the user asks for more detail). Use fashion-forward language but stay accessible."""


def _call_claude(messages: list[dict], system: str = _SYSTEM) -> str:
    response = _bedrock.converse(
        modelId=CLAUDE_MODEL,
        system=[{"text": system}],
        messages=messages,
        inferenceConfig={"maxTokens": 512, "temperature": 0.7},
    )
    return response["output"]["message"]["content"][0]["text"].strip()


def _extract_designer_season(question: str) -> dict:
    """Use Claude to pull designer + season out of a natural language question."""
    prompt = f"""Extract the designer and season from this fashion question.
Return ONLY valid JSON, no explanation:
{{"designer": "slug", "season": "spring-YYYY or fall-YYYY"}}

Rules:
- designer: lowercase slug with hyphens (chanel, louis-vuitton, miu-miu, balenciaga)
- season: must be "spring-YYYY" or "fall-YYYY" format
- If year is ambiguous (e.g. "2023" without spring/fall), try both spring and fall
- If either is missing or unclear, use null

Question: {question}"""

    raw = _call_claude(
        [{"role": "user", "content": [{"text": prompt}]}],
        system="You extract structured data from text. Return only valid JSON.",
    )
    try:
        # strip markdown fences if present
        text = raw.strip().strip("```json").strip("```").strip()
        return json.loads(text)
    except Exception:
        return {"designer": None, "season": None}


def _get_or_fetch_insights(designer: str, season: str) -> dict | None:
    """Return cached insights or run the full pipeline to generate them."""
    cached = get_cached_insights(designer, season)
    if cached:
        return cached

    print(f"\n  No cached insights for {designer} / {season}.")
    print(f"  Running full analysis (scraping + Claude synthesis)...")
    try:
        return analyze(designer=designer, season=season)
    except Exception as e:
        print(f"  Analysis failed: {e}")
        return None


def _insights_to_context(insights: dict) -> str:
    """Format insights dict as readable context for Claude."""
    lines = [
        f"Designer: {insights.get('designer', '').title()}",
        f"Season: {insights.get('season', '')}",
        f"Data quality: {insights.get('data_quality', 'unknown')}",
        f"Sources used: {', '.join(insights.get('sources_used', []))}",
        "",
        f"Critic themes: {', '.join(insights.get('critic_themes', []))}",
        f"Visual themes (from runway images): {', '.join(insights.get('visual_themes', []))}",
        "",
        "Where critics and visuals agree:",
        *[f"  - {a}" for a in insights.get("agreements", [])],
        "",
        "Interesting tensions / divergences:",
        *[f"  - {t}" for t in insights.get("tensions", [])],
        "",
        f"Narrative: {insights.get('narrative', '')}",
    ]
    return "\n".join(lines)


def chat():
    print("\nFashion Intelligence Chatbot")
    print("─" * 40)
    print("Ask about any designer and season.")
    print("Type 'quit' or 'exit' to stop.\n")

    history: list[dict] = []
    current_insights: dict | None = None

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit", "bye"}:
            print("Goodbye!")
            break

        # Try to extract designer/season from the question
        extracted = _extract_designer_season(user_input)
        designer = extracted.get("designer")
        season = extracted.get("season")

        # If we got a new designer/season, fetch insights for it
        if designer and season:
            insights = _get_or_fetch_insights(designer, season)
            if insights:
                current_insights = insights
                context_block = f"\n\n[FASHION DATA]\n{_insights_to_context(insights)}\n[END DATA]"
            else:
                context_block = f"\n\n[No data available for {designer} {season}]"
        elif current_insights:
            # Follow-up question — reuse current insights
            context_block = f"\n\n[FASHION DATA]\n{_insights_to_context(current_insights)}\n[END DATA]"
        else:
            context_block = ""

        # Append user message (with context injected)
        history.append({
            "role": "user",
            "content": [{"text": user_input + context_block}],
        })

        # Call Claude
        try:
            reply = _call_claude(history)
        except Exception as e:
            print(f"Bot: (error: {e})\n")
            history.pop()
            continue

        # Append assistant reply to history
        history.append({
            "role": "assistant",
            "content": [{"text": reply}],
        })

        print(f"\nBot: {reply}\n")


if __name__ == "__main__":
    chat()
