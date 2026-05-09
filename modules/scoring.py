"""Simple investment scoring primitives."""

from __future__ import annotations

import pandas as pd


def score_ticker(snapshot: dict[str, object], history: pd.DataFrame) -> dict[str, object]:
    """Create transparent long/short factor scores from snapshot and price data."""

    momentum = _momentum_score(history)
    quality = _quality_score(snapshot)
    valuation = _valuation_score(snapshot)
    risk = _risk_score(snapshot, history)

    total = round((0.35 * momentum) + (0.25 * quality) + (0.25 * valuation) + (0.15 * risk), 1)
    stance = "Long" if total >= 65 else "Short" if total <= 40 else "Watch"

    return {
        "stance": stance,
        "total_score": total,
        "momentum_score": momentum,
        "quality_score": quality,
        "valuation_score": valuation,
        "risk_score": risk,
        "summary": _summary_for_score(stance, total),
    }


def score_ideas(ideas: pd.DataFrame) -> pd.DataFrame:
    """Add a quick score and suggested stance to a daily ideas DataFrame."""

    if ideas.empty:
        return ideas

    scored = ideas.copy()
    scored["idea_score"] = scored.apply(_score_idea_row, axis=1)
    scored["stance"] = scored["idea_score"].apply(
        lambda score: "Long" if score >= 65 else "Short" if score <= 40 else "Watch"
    )
    return scored.sort_values("idea_score", ascending=False)


def _score_idea_row(row: pd.Series) -> float:
    score = 50.0
    score += _bounded(_as_float(row.get("six_month_return")) * 100, -20, 20)
    score += _bounded(_as_float(row.get("profit_margin")) * 60, -10, 15)
    score += _bounded(_as_float(row.get("revenue_growth")) * 50, -10, 15)

    forward_pe = row.get("forward_pe")
    if _is_number(forward_pe) and forward_pe > 0:
        score += _bounded((25 - forward_pe) * 0.6, -12, 12)

    beta = row.get("beta")
    if _is_number(beta) and beta > 1.4:
        score -= min((beta - 1.4) * 8, 10)

    return round(_bounded(score, 0, 100), 1)


def _momentum_score(history: pd.DataFrame) -> float:
    if history.empty or "Close" not in history:
        return 50.0

    closes = history["Close"].dropna()
    if len(closes) < 30:
        return 50.0

    short = closes.tail(min(63, len(closes)))
    long = closes.tail(min(252, len(closes)))
    short_return = (short.iloc[-1] / short.iloc[0]) - 1 if short.iloc[0] else 0
    long_return = (long.iloc[-1] / long.iloc[0]) - 1 if long.iloc[0] else 0
    score = 50 + (short_return * 120) + (long_return * 60)
    return round(_bounded(score, 0, 100), 1)


def _quality_score(snapshot: dict[str, object]) -> float:
    score = 50.0
    score += _bounded(_as_float(snapshot.get("profit_margin")) * 80, -20, 25)
    score += _bounded(_as_float(snapshot.get("revenue_growth")) * 70, -20, 25)
    return round(_bounded(score, 0, 100), 1)


def _valuation_score(snapshot: dict[str, object]) -> float:
    forward_pe = snapshot.get("forward_pe") or snapshot.get("trailing_pe")
    if not _is_number(forward_pe) or forward_pe <= 0:
        return 50.0
    score = 75 - (forward_pe - 15) * 1.4
    return round(_bounded(score, 0, 100), 1)


def _risk_score(snapshot: dict[str, object], history: pd.DataFrame) -> float:
    score = 70.0
    beta = snapshot.get("beta")
    if _is_number(beta):
        score -= max(beta - 1, 0) * 18
        score += max(1 - beta, 0) * 8

    if not history.empty and "Close" in history:
        volatility = history["Close"].pct_change().dropna().std()
        if pd.notna(volatility):
            score -= min(float(volatility) * 600, 25)

    return round(_bounded(score, 0, 100), 1)


def _summary_for_score(stance: str, total: float) -> str:
    if stance == "Long":
        return f"Constructive setup with a {total}/100 composite score."
    if stance == "Short":
        return f"Weak setup with a {total}/100 composite score."
    return f"Mixed setup with a {total}/100 composite score."


def _bounded(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, float(value)))


def _as_float(value: object) -> float:
    return float(value) if _is_number(value) else 0.0


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and pd.notna(value)
