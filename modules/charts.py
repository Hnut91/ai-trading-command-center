"""Plotly chart builders for research views."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def price_volume_chart(history: pd.DataFrame, ticker: str) -> go.Figure:
    """Create a price and volume chart from yfinance history."""

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.72, 0.28],
    )

    if history.empty:
        fig.update_layout(title=f"{ticker.upper()} price history unavailable")
        return fig

    chart = history.copy()
    chart["SMA 20"] = chart["Close"].rolling(20).mean()
    chart["SMA 50"] = chart["Close"].rolling(50).mean()

    fig.add_trace(
        go.Scatter(x=chart["Date"], y=chart["Close"], name="Close", line=dict(width=2)),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=chart["Date"], y=chart["SMA 20"], name="SMA 20", line=dict(width=1)),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=chart["Date"], y=chart["SMA 50"], name="SMA 50", line=dict(width=1)),
        row=1,
        col=1,
    )

    if "Volume" in chart:
        fig.add_trace(
            go.Bar(x=chart["Date"], y=chart["Volume"], name="Volume", marker_opacity=0.35),
            row=2,
            col=1,
        )

    fig.update_layout(
        title=f"{ticker.upper()} Price, Trend, and Volume",
        height=520,
        margin=dict(l=20, r=20, t=50, b=20),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    return fig


def backtest_equity_chart(results: pd.DataFrame, ticker: str) -> go.Figure:
    """Create an equity curve chart for backtest output."""

    fig = go.Figure()
    if results.empty:
        fig.update_layout(title=f"{ticker.upper()} backtest unavailable")
        return fig

    fig.add_trace(go.Scatter(x=results["Date"], y=results["equity"], name="Strategy Equity"))
    fig.add_trace(go.Scatter(x=results["Date"], y=results["buy_hold_equity"], name="Buy & Hold"))
    fig.update_layout(
        title=f"{ticker.upper()} Moving-Average Crossover Backtest",
        height=420,
        margin=dict(l=20, r=20, t=50, b=20),
        hovermode="x unified",
    )
    return fig
