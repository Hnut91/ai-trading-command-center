"""AI Long/Short Command Center Streamlit app."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from modules.market_data import DEFAULT_IDEAS, get_daily_ideas, get_price_history, get_ticker_snapshot
from modules.memo_agent import generate_investment_memo
from modules.scoring import score_ideas, score_ticker


st.set_page_config(
    page_title="AI Long/Short Command Center",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)


def main() -> None:
    _init_state()

    st.title("AI Long/Short Command Center")
    st.caption("AI-native hedge fund research dashboard for idea generation, memo writing, and paper tracking.")

    tabs = st.tabs(["Daily Ideas", "Ticker Research", "Paper Portfolio", "Watchlist", "Agent Log"])

    with tabs[0]:
        render_daily_ideas()
    with tabs[1]:
        render_ticker_research()
    with tabs[2]:
        render_portfolio()
    with tabs[3]:
        render_watchlist()
    with tabs[4]:
        render_agent_log()


def render_daily_ideas() -> None:
    st.subheader("Daily Ideas")
    default_text = ", ".join(DEFAULT_IDEAS)
    tickers_text = st.text_input("Universe", value=default_text)
    tickers = [ticker.strip().upper() for ticker in tickers_text.split(",") if ticker.strip()]

    if st.button("Refresh Ideas", type="primary"):
        with st.spinner("Pulling market data..."):
            ideas = score_ideas(get_daily_ideas(tickers))
            st.session_state["ideas"] = ideas
            _log(f"Refreshed daily ideas for {', '.join(tickers)}")

    ideas = st.session_state.get("ideas")
    if isinstance(ideas, pd.DataFrame) and not ideas.empty:
        st.dataframe(
            ideas[
                [
                    "ticker",
                    "name",
                    "stance",
                    "idea_score",
                    "price",
                    "six_month_return",
                    "forward_pe",
                    "profit_margin",
                    "revenue_growth",
                    "beta",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Refresh ideas to load a scored universe.")


def render_ticker_research() -> None:
    st.subheader("Ticker Research")
    left, right = st.columns([1, 2])

    with left:
        ticker = st.text_input("Ticker", value="MSFT").upper()
        period = st.selectbox("Price history", ["3mo", "6mo", "1y", "2y", "5y"], index=2)
        notes = st.text_area("Analyst notes", placeholder="Catalysts, concerns, variant perception...")
        run_research = st.button("Run Research", type="primary")

    if run_research and ticker:
        with st.spinner(f"Researching {ticker}..."):
            snapshot = get_ticker_snapshot(ticker)
            history = get_price_history(ticker, period=period)
            score = score_ticker(snapshot.as_dict(), history)
            memo = generate_investment_memo(ticker, snapshot.as_dict(), score, notes)

            st.session_state["research"] = {
                "ticker": ticker,
                "snapshot": snapshot.as_dict(),
                "history": history,
                "score": score,
                "memo": memo,
            }
            _log(f"Generated research memo for {ticker}")

    research = st.session_state.get("research")
    if research:
        snapshot = research["snapshot"]
        score = research["score"]
        history = research["history"]

        with right:
            metric_cols = st.columns(4)
            metric_cols[0].metric("Stance", score["stance"])
            metric_cols[1].metric("Score", f"{score['total_score']}/100")
            metric_cols[2].metric("Price", _money(snapshot.get("price")))
            metric_cols[3].metric("Forward P/E", _number(snapshot.get("forward_pe")))

            if isinstance(history, pd.DataFrame) and not history.empty:
                st.line_chart(history.set_index("Date")["Close"])

        st.markdown("### AI Investment Memo")
        st.markdown(research["memo"])

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Add To Watchlist"):
                _add_watchlist(research["ticker"], score["stance"], score["total_score"])
        with c2:
            if st.button("Add Paper Position"):
                _add_position(research["ticker"], score["stance"], snapshot.get("price"))


def render_portfolio() -> None:
    st.subheader("Paper Portfolio")

    with st.form("position_form", clear_on_submit=True):
        cols = st.columns(5)
        ticker = cols[0].text_input("Ticker")
        side = cols[1].selectbox("Side", ["Long", "Short"])
        quantity = cols[2].number_input("Quantity", min_value=0.0, step=1.0)
        entry_price = cols[3].number_input("Entry Price", min_value=0.0, step=1.0)
        submitted = cols[4].form_submit_button("Add")

    if submitted and ticker:
        _add_position(ticker.upper(), side, entry_price, quantity)

    portfolio = pd.DataFrame(st.session_state["portfolio"])
    if portfolio.empty:
        st.info("No paper positions yet.")
        return

    st.dataframe(portfolio, use_container_width=True, hide_index=True)


def render_watchlist() -> None:
    st.subheader("Watchlist")

    with st.form("watchlist_form", clear_on_submit=True):
        cols = st.columns([1, 1, 1, 2])
        ticker = cols[0].text_input("Ticker")
        stance = cols[1].selectbox("Stance", ["Long", "Watch", "Short"])
        score = cols[2].number_input("Score", min_value=0.0, max_value=100.0, value=50.0)
        note = cols[3].text_input("Note")
        submitted = st.form_submit_button("Add To Watchlist")

    if submitted and ticker:
        _add_watchlist(ticker.upper(), stance, score, note)

    watchlist = pd.DataFrame(st.session_state["watchlist"])
    if watchlist.empty:
        st.info("No watchlist names yet.")
    else:
        st.dataframe(watchlist, use_container_width=True, hide_index=True)


def render_agent_log() -> None:
    st.subheader("Agent Log")
    if not st.session_state["agent_log"]:
        st.info("No agent activity yet.")
        return

    for item in reversed(st.session_state["agent_log"]):
        st.write(f"**{item['time']}** - {item['message']}")


def _init_state() -> None:
    st.session_state.setdefault("portfolio", [])
    st.session_state.setdefault("watchlist", [])
    st.session_state.setdefault("agent_log", [])


def _add_watchlist(ticker: str, stance: str, score: float, note: str = "") -> None:
    st.session_state["watchlist"].append(
        {"ticker": ticker.upper(), "stance": stance, "score": score, "note": note, "added": _timestamp()}
    )
    _log(f"Added {ticker.upper()} to watchlist")
    st.success(f"Added {ticker.upper()} to watchlist.")


def _add_position(ticker: str, side: str, entry_price: float | None, quantity: float = 1.0) -> None:
    st.session_state["portfolio"].append(
        {
            "ticker": ticker.upper(),
            "side": side,
            "quantity": quantity,
            "entry_price": entry_price or 0,
            "opened": _timestamp(),
        }
    )
    _log(f"Added {side.lower()} paper position in {ticker.upper()}")
    st.success(f"Added {ticker.upper()} paper position.")


def _log(message: str) -> None:
    st.session_state["agent_log"].append({"time": _timestamp(), "message": message})


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _money(value: object) -> str:
    return f"${value:,.2f}" if isinstance(value, (int, float)) else "n/a"


def _number(value: object) -> str:
    return f"{value:,.1f}" if isinstance(value, (int, float)) else "n/a"


if __name__ == "__main__":
    main()
