"""OpenAI-powered investment memo generation."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


SYSTEM_PROMPT = """
You are an institutional long/short equity analyst. Write crisp, balanced
investment memos for a hedge fund research dashboard. Separate facts from
judgment, highlight both bull and bear cases, and never claim certainty.
This is research assistance, not financial advice.
""".strip()


def generate_investment_memo(
    ticker: str,
    snapshot: dict[str, Any],
    score: dict[str, Any],
    notes: str = "",
    model: str = "gpt-4o-mini",
) -> str:
    """Generate an investment memo with the OpenAI API."""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _offline_memo(ticker, snapshot, score, notes)

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        temperature=0.4,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _memo_prompt(ticker=ticker, snapshot=snapshot, score=score, notes=notes),
            },
        ],
    )
    return response.choices[0].message.content or ""


def _memo_prompt(ticker: str, snapshot: dict[str, Any], score: dict[str, Any], notes: str) -> str:
    return f"""
Create an investment memo for {ticker.upper()}.

Company snapshot:
{snapshot}

Quant/factor score:
{score}

Analyst notes:
{notes or "No additional notes provided."}

Use this format:
1. Recommendation
2. Business Snapshot
3. Long Thesis
4. Short Thesis / Risks
5. Key Metrics To Watch
6. Next Research Steps
""".strip()


def _offline_memo(ticker: str, snapshot: dict[str, Any], score: dict[str, Any], notes: str) -> str:
    """Fallback memo shown when OPENAI_API_KEY is absent."""

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    name = snapshot.get("name") or ticker.upper()
    stance = score.get("stance", "Watch")
    total = score.get("total_score", "n/a")

    return f"""
## {ticker.upper()} Investment Memo

Generated: {generated_at}

### 1. Recommendation
Preliminary stance: **{stance}**. Composite score: **{total}/100**.

### 2. Business Snapshot
{name} operates in {snapshot.get("sector") or "an unspecified sector"} / {snapshot.get("industry") or "unspecified industry"}.

### 3. Long Thesis
- Momentum, quality, valuation, and risk factors should be reviewed against the scorecard.
- Current price: {snapshot.get("price") or "n/a"}.

### 4. Short Thesis / Risks
- Validate yfinance fundamentals against filings and company guidance.
- Revisit crowded positioning, earnings risk, and macro sensitivity before sizing.

### 5. Key Metrics To Watch
- Revenue growth: {snapshot.get("revenue_growth") or "n/a"}
- Profit margin: {snapshot.get("profit_margin") or "n/a"}
- Forward P/E: {snapshot.get("forward_pe") or "n/a"}
- Beta: {snapshot.get("beta") or "n/a"}

### 6. Next Research Steps
- Read the latest 10-Q/10-K and earnings transcript.
- Compare valuation to direct peers.
- Build a catalyst calendar and downside scenario.

Analyst notes: {notes or "None."}

Set `OPENAI_API_KEY` in `.env` to enable AI-generated memos.
""".strip()
