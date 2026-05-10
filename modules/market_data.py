"""Market data access helpers for the AI Long/Short Command Center."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

import pandas as pd
import yfinance as yf


DEFAULT_IDEAS = ["MSFT", "NVDA", "AAPL", "GOOGL", "AMZN", "META", "TSLA", "JPM"]


@dataclass(frozen=True)
class TickerSnapshot:
    """Compact ticker snapshot used by the UI and memo agent."""

    ticker: str
    name: str
    price: float | None
    market_cap: int | None
    sector: str | None
    industry: str | None
    trailing_pe: float | None
    forward_pe: float | None
    profit_margin: float | None
    revenue_growth: float | None
    beta: float | None
    dividend_yield: float | None

    def as_dict(self) -> dict[str, object]:
        return {
            "ticker": self.ticker,
            "name": self.name,
            "price": self.price,
            "market_cap": self.market_cap,
            "sector": self.sector,
            "industry": self.industry,
            "trailing_pe": self.trailing_pe,
            "forward_pe": self.forward_pe,
            "profit_margin": self.profit_margin,
            "revenue_growth": self.revenue_growth,
            "beta": self.beta,
            "dividend_yield": self.dividend_yield,
        }


def normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def get_price_history(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
    start: date | str | None = None,
) -> pd.DataFrame:
    """Download historical OHLCV data from yfinance."""

    symbol = normalize_ticker(ticker)
    if not symbol:
        return pd.DataFrame()

    download_kwargs = {
        "tickers": symbol,
        "interval": interval,
        "auto_adjust": True,
        "progress": False,
        "threads": False,
    }
    if start:
        download_kwargs["start"] = start
    else:
        download_kwargs["period"] = period

    history = yf.download(**download_kwargs)
    if history.empty:
        return history

    history = history.reset_index()
    if isinstance(history.columns, pd.MultiIndex):
        history.columns = [col[0] for col in history.columns]
    return history


def get_ticker_snapshot(ticker: str) -> TickerSnapshot:
    """Fetch a current company snapshot from yfinance."""

    symbol = normalize_ticker(ticker)
    if not symbol:
        raise ValueError("Ticker is required.")

    stock = yf.Ticker(symbol)
    info = stock.get_info() or {}

    return TickerSnapshot(
        ticker=symbol,
        name=info.get("longName") or info.get("shortName") or symbol,
        price=_first_number(info, "currentPrice", "regularMarketPrice", "previousClose"),
        market_cap=_first_int(info, "marketCap"),
        sector=info.get("sector"),
        industry=info.get("industry"),
        trailing_pe=_first_number(info, "trailingPE"),
        forward_pe=_first_number(info, "forwardPE"),
        profit_margin=_first_number(info, "profitMargins"),
        revenue_growth=_first_number(info, "revenueGrowth"),
        beta=_first_number(info, "beta"),
        dividend_yield=_first_number(info, "dividendYield"),
    )


def get_daily_ideas(tickers: Iterable[str] = DEFAULT_IDEAS) -> pd.DataFrame:
    """Build a quick idea sheet for common liquid stocks."""

    rows: list[dict[str, object]] = []
    for ticker in tickers:
        try:
            snapshot = get_ticker_snapshot(ticker)
            history = get_price_history(ticker, period="6mo")
            latest_return = _period_return(history)
            row = snapshot.as_dict()
            row["six_month_return"] = latest_return
            rows.append(row)
        except Exception:
            row = TickerSnapshot(
                ticker=normalize_ticker(ticker),
                name="Unavailable",
                price=None,
                market_cap=None,
                sector=None,
                industry=None,
                trailing_pe=None,
                forward_pe=None,
                profit_margin=None,
                revenue_growth=None,
                beta=None,
                dividend_yield=None,
            ).as_dict()
            row["six_month_return"] = None
            rows.append(row)

    return pd.DataFrame(rows)


def _period_return(history: pd.DataFrame) -> float | None:
    if history.empty or "Close" not in history:
        return None
    closes = history["Close"].dropna()
    if len(closes) < 2 or closes.iloc[0] == 0:
        return None
    return float((closes.iloc[-1] / closes.iloc[0]) - 1)


def _first_number(source: dict[str, object], *keys: str) -> float | None:
    for key in keys:
        value = source.get(key)
        if isinstance(value, (int, float)) and pd.notna(value):
            return float(value)
    return None


def _first_int(source: dict[str, object], *keys: str) -> int | None:
    for key in keys:
        value = source.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, float) and pd.notna(value):
            return int(value)
    return None
