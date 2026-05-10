"""News and catalyst helpers for ticker research."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import yfinance as yf
from openai import OpenAI


POSITIVE_KEYWORDS = ["beat", "upgrade", "guidance", "partnership", "launch", "approval"]
NEGATIVE_KEYWORDS = ["lawsuit", "investigation", "downgrade", "miss", "fraud", "recall"]
CATALYST_KEYWORDS = ["earnings", "guidance", "approval", "launch", "partnership", "analyst", "deal"]


def get_yfinance_news(ticker: str, limit: int = 10) -> list[dict[str, Any]]:
    """Pull recent yfinance news and normalize it for the app."""

    symbol = ticker.strip().upper()
    if not symbol:
        return []

    try:
        raw_news = yf.Ticker(symbol).news or []
    except Exception:
        return []

    normalized = [_normalize_news_item(item) for item in raw_news[:limit]]
    return [item for item in normalized if item.get("title")]


def catalyst_score(news_items: list[dict[str, Any]]) -> int:
    """Score catalyst relevance from 0-100 using transparent keyword rules."""

    if not news_items:
        return 20

    score = 42 + min(len(news_items), 10) * 3
    combined_text = " ".join(
        f"{item.get('title', '')} {item.get('summary', '')}".lower() for item in news_items
    )

    positive_hits = sum(1 for keyword in POSITIVE_KEYWORDS if keyword in combined_text)
    negative_hits = sum(1 for keyword in NEGATIVE_KEYWORDS if keyword in combined_text)
    catalyst_hits = sum(1 for keyword in CATALYST_KEYWORDS if keyword in combined_text)

    score += min(catalyst_hits * 7, 24)
    score += min(positive_hits * 6, 18)
    score -= min(negative_hits * 8, 28)

    recent_hits = sum(1 for item in news_items if _is_recent(item.get("published_at")))
    score += min(recent_hits * 4, 16)

    return int(max(0, min(100, score)))


def top_headline(news_items: list[dict[str, Any]]) -> str:
    if not news_items:
        return "No recent headline available"
    return str(news_items[0].get("title") or "No recent headline available")


def combined_scanner_score(simple: float, catalyst: int) -> float:
    return round((simple * 0.7) + (catalyst * 0.3), 1)


def generate_catalyst_summary(
    ticker: str,
    news_items: list[dict[str, Any]],
    market_data: dict[str, Any],
    score: dict[str, Any],
    api_key: str | None = None,
    model: str = "gpt-4o-mini",
) -> str:
    """Use AI to summarize catalysts for one selected ticker."""

    local_score = catalyst_score(news_items)
    if not api_key:
        return _offline_catalyst_summary(ticker, news_items, local_score)

    headlines = [
        {
            "title": item.get("title"),
            "publisher": item.get("publisher"),
            "published_at": item.get("published_at"),
            "summary": item.get("summary"),
        }
        for item in news_items[:8]
    ]

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a concise long/short equity catalyst analyst. "
                        "Separate facts from interpretation. This is research assistance, not investment advice."
                    ),
                },
                {
                    "role": "user",
                    "content": f"""
Summarize catalysts for {ticker.upper()}.

Recent news:
{headlines or "No recent yfinance news available."}

Market snapshot:
{market_data}

Quant score:
{score}

Catalyst score:
{local_score}/100

Use this concise format:
1. Key Catalysts
2. Bullish Interpretation
3. Bearish Interpretation
4. Watchlist View: Long Watch, Short Watch, or Avoid
""".strip(),
                },
            ],
        )
        return response.choices[0].message.content or _offline_catalyst_summary(ticker, news_items, local_score)
    except Exception:
        return _offline_catalyst_summary(ticker, news_items, local_score)


def _normalize_news_item(item: dict[str, Any]) -> dict[str, Any]:
    content = item.get("content") if isinstance(item.get("content"), dict) else {}
    link = item.get("link") or item.get("url") or _nested_url(content.get("canonicalUrl"))
    publisher = item.get("publisher") or content.get("provider", {}).get("displayName")
    title = item.get("title") or content.get("title")
    summary = item.get("summary") or content.get("summary") or content.get("description")
    published_at = _published_at(item, content)

    return {
        "title": title or "",
        "publisher": publisher or "Unknown",
        "link": link or "",
        "published_at": published_at,
        "summary": summary or "",
    }


def _published_at(item: dict[str, Any], content: dict[str, Any]) -> str:
    raw_value = (
        item.get("providerPublishTime")
        or item.get("providerPublishTimeInMillis")
        or item.get("pubDate")
        or content.get("pubDate")
        or content.get("displayTime")
    )

    if isinstance(raw_value, (int, float)):
        if raw_value > 10_000_000_000:
            raw_value = raw_value / 1000
        return datetime.fromtimestamp(raw_value, tz=timezone.utc).strftime("%Y-%m-%d")

    if isinstance(raw_value, str):
        try:
            return datetime.fromisoformat(raw_value.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        except ValueError:
            return raw_value[:10]

    return ""


def _nested_url(value: Any) -> str | None:
    if isinstance(value, dict):
        return value.get("url")
    if isinstance(value, str):
        return value
    return None


def _is_recent(published_at: object) -> bool:
    if not isinstance(published_at, str) or not published_at:
        return False
    try:
        published = datetime.fromisoformat(published_at[:10]).replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    age_days = (datetime.now(timezone.utc) - published).days
    return age_days <= 14


def _offline_catalyst_summary(ticker: str, news_items: list[dict[str, Any]], score: int) -> str:
    view = "Long Watch" if score >= 70 else "Short Watch" if score <= 45 else "Avoid"
    headline = top_headline(news_items)
    if not news_items:
        return f"""
### Catalyst Summary

1. Key Catalysts: No recent yfinance headlines were available for {ticker.upper()}.
2. Bullish Interpretation: No clear news catalyst is visible from the current feed.
3. Bearish Interpretation: Lack of fresh catalysts can reduce near-term conviction.
4. Watchlist View: {view}. Catalyst score: {score}/100.
""".strip()

    return f"""
### Catalyst Summary

1. Key Catalysts: Top headline is "{headline}".
2. Bullish Interpretation: Recent coverage may support renewed investor attention.
3. Bearish Interpretation: Headline context needs validation before position sizing.
4. Watchlist View: {view}. Catalyst score: {score}/100.
""".strip()
