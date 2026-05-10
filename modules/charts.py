"""Plotly chart builders for research views."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


CHART_TEMPLATE = "plotly_dark"
PAPER_BG = "#0d1713"
PLOT_BG = "#07100d"
GRID_COLOR = "#1f3d32"
TEXT_COLOR = "#e8fff3"
MUTED_COLOR = "#8fa89b"
GREEN = "#00ff88"
BLUE = "#5ad7ff"
AMBER = "#ffc857"


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
        go.Scatter(x=chart["Date"], y=chart["Close"], name="Close", line=dict(width=2, color=GREEN)),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=chart["Date"], y=chart["SMA 20"], name="SMA 20", line=dict(width=1.4, color=BLUE)),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=chart["Date"], y=chart["SMA 50"], name="SMA 50", line=dict(width=1.4, color=AMBER)),
        row=1,
        col=1,
    )

    if "Volume" in chart:
        fig.add_trace(
            go.Bar(x=chart["Date"], y=chart["Volume"], name="Volume", marker_color="#1f3d32", marker_opacity=0.72),
            row=2,
            col=1,
        )

    fig.update_layout(
        title=f"{ticker.upper()} Price, Trend, and Volume",
        template=CHART_TEMPLATE,
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color=TEXT_COLOR),
        height=520,
        margin=dict(l=20, r=20, t=50, b=20),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)
    fig.update_yaxes(title_text="Price", row=1, col=1, gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)
    fig.update_yaxes(title_text="Volume", row=2, col=1, gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)
    return fig


def backtest_equity_chart(results: pd.DataFrame, ticker: str) -> go.Figure:
    """Create an equity curve chart for backtest output."""

    fig = go.Figure()
    if results.empty:
        fig.update_layout(title=f"{ticker.upper()} backtest unavailable")
        return fig

    fig.add_trace(go.Scatter(x=results["Date"], y=results["equity"], name="Strategy Equity", line=dict(color=GREEN)))
    fig.add_trace(go.Scatter(x=results["Date"], y=results["buy_hold_equity"], name="Buy & Hold", line=dict(color=BLUE)))
    if {"short_ma", "long_ma"}.issubset(results.columns):
        buys = results[results["trade"] > 0]
        fig.add_trace(
            go.Scatter(
                x=buys["Date"],
                y=buys["equity"],
                mode="markers",
                name="Trade",
                marker=dict(size=8, color=AMBER),
            )
        )
    fig.update_layout(
        title=f"{ticker.upper()} Moving-Average Crossover Backtest",
        template=CHART_TEMPLATE,
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color=TEXT_COLOR),
        height=420,
        margin=dict(l=20, r=20, t=50, b=20),
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)
    fig.update_yaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)
    return fig
