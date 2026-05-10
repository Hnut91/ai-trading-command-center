"""Lightweight backtesting utilities."""

from __future__ import annotations

import pandas as pd


def moving_average_crossover_backtest(
    history: pd.DataFrame,
    short_window: int = 20,
    long_window: int = 50,
    starting_cash: float = 100_000,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Run a simple long/cash moving-average crossover backtest."""

    if history.empty or "Close" not in history:
        return pd.DataFrame(), _empty_metrics(starting_cash)

    if short_window >= long_window:
        raise ValueError("Short window must be below long window.")

    results = history[["Date", "Close"]].dropna().copy()
    if len(results) <= long_window:
        return pd.DataFrame(), _empty_metrics(starting_cash)

    results["short_ma"] = results["Close"].rolling(short_window).mean()
    results["long_ma"] = results["Close"].rolling(long_window).mean()
    results["signal"] = (results["short_ma"] > results["long_ma"]).astype(int)
    results["position"] = results["signal"].shift(1).fillna(0)
    results["trade"] = results["position"].diff().abs().fillna(0)
    results["asset_return"] = results["Close"].pct_change().fillna(0)
    results["strategy_return"] = results["position"] * results["asset_return"]
    results["equity"] = starting_cash * (1 + results["strategy_return"]).cumprod()
    results["buy_hold_equity"] = starting_cash * (1 + results["asset_return"]).cumprod()

    metrics = _metrics(results, starting_cash)
    return results, metrics


def _metrics(results: pd.DataFrame, starting_cash: float) -> dict[str, float]:
    ending_equity = float(results["equity"].iloc[-1])
    buy_hold_equity = float(results["buy_hold_equity"].iloc[-1])
    total_return = (ending_equity / starting_cash) - 1
    buy_hold_return = (buy_hold_equity / starting_cash) - 1
    number_of_trades = int(results["trade"].sum())
    daily_returns = results["strategy_return"].dropna()
    volatility = float(daily_returns.std() * (252**0.5)) if len(daily_returns) > 1 else 0.0
    sharpe = float((daily_returns.mean() * 252) / volatility) if volatility else 0.0
    max_drawdown = _max_drawdown(results["equity"])

    return {
        "ending_equity": round(ending_equity, 2),
        "total_return": round(total_return, 4),
        "buy_hold_return": round(buy_hold_return, 4),
        "number_of_trades": number_of_trades,
        "volatility": round(volatility, 4),
        "sharpe": round(sharpe, 2),
        "max_drawdown": round(max_drawdown, 4),
    }


def _max_drawdown(equity: pd.Series) -> float:
    running_max = equity.cummax()
    drawdown = (equity / running_max) - 1
    return float(drawdown.min())


def _empty_metrics(starting_cash: float) -> dict[str, float]:
    return {
        "ending_equity": starting_cash,
        "total_return": 0.0,
        "buy_hold_return": 0.0,
        "number_of_trades": 0,
        "volatility": 0.0,
        "sharpe": 0.0,
        "max_drawdown": 0.0,
    }
