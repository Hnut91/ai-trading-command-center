"""AI Long/Short Command Center Streamlit app."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from modules.backtesting import moving_average_crossover_backtest
from modules.charts import backtest_equity_chart, price_volume_chart
from modules.market_data import DEFAULT_IDEAS, get_daily_ideas, get_price_history, get_ticker_snapshot
from modules.memo_agent import generate_investment_memo
from modules.paper_trading import alpaca_ready, create_simulated_order
from modules.scoring import score_ideas, score_ticker, simple_score


SCANNER_UNIVERSE = ["AAPL", "MSFT", "NVDA", "META", "AMZN", "GOOGL", "TSLA"]


st.set_page_config(
    page_title="AI Long/Short Command Center",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)


def main() -> None:
    _init_state()

    st.title("AI Long/Short Command Center")
    st.caption("AI-native hedge fund research dashboard for idea generation, memo writing, and paper tracking.")

    tabs = st.tabs(
        [
            "Daily Ideas",
            "Daily Scanner",
            "Ticker Research",
            "Backtesting",
            "Paper Trading",
            "Watchlist",
            "Agent Log",
        ]
    )

    with tabs[0]:
        render_daily_ideas()
    with tabs[1]:
        render_daily_scanner()
    with tabs[2]:
        render_ticker_research()
    with tabs[3]:
        render_backtesting()
    with tabs[4]:
        render_paper_trading()
    with tabs[5]:
        render_watchlist()
    with tabs[6]:
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
            memo = generate_investment_memo(
                ticker,
                snapshot.as_dict(),
                score,
                notes,
                api_key=_secret_value("OPENAI_API_KEY"),
            )

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
                st.plotly_chart(price_volume_chart(history, research["ticker"]), use_container_width=True)

        st.markdown("### AI Investment Memo")
        st.markdown(research["memo"])

        st.markdown("### TradingView")
        tradingview_url = _tradingview_url(research["ticker"])
        components.html(_tradingview_embed(research["ticker"]), height=520, scrolling=False)
        st.link_button("Open on TradingView", tradingview_url)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Add To Watchlist"):
                _add_watchlist(research["ticker"], score["stance"], score["total_score"])
        with c2:
            if st.button("Add Paper Position"):
                _add_position(research["ticker"], score["stance"], snapshot.get("price"))


def render_daily_scanner() -> None:
    st.subheader("Daily Scanner")
    st.caption("Ranks the core mega-cap universe with simple_score using recent trend and volatility.")

    if st.button("Run Daily Scanner", type="primary"):
        rows = []
        with st.spinner("Scanning liquid mega-cap names..."):
            for ticker in SCANNER_UNIVERSE:
                try:
                    history = get_price_history(ticker, period="6mo")
                    snapshot = get_ticker_snapshot(ticker)
                    score = simple_score(history)
                    one_month_return = _window_return(history, 21)
                    three_month_return = _window_return(history, 63)
                except Exception:
                    snapshot = None
                    score = 50.0
                    one_month_return = None
                    three_month_return = None

                rows.append(
                    {
                        "ticker": ticker,
                        "name": snapshot.name if snapshot else "Unavailable",
                        "price": snapshot.price if snapshot else None,
                        "score": score,
                        "classification": _scanner_classification(score),
                        "explanation": _scanner_explanation(score, one_month_return, three_month_return),
                        "one_month_return": one_month_return,
                        "three_month_return": three_month_return,
                    }
                )

        scanner = pd.DataFrame(rows).sort_values("score", ascending=False)
        st.session_state["scanner"] = scanner
        _log("Ran daily scanner")

    scanner = st.session_state.get("scanner")
    if isinstance(scanner, pd.DataFrame) and not scanner.empty:
        st.dataframe(scanner, use_container_width=True, hide_index=True)
    else:
        st.info("Run the scanner to rank AAPL, MSFT, NVDA, META, AMZN, GOOGL, and TSLA.")


def render_backtesting() -> None:
    st.subheader("Backtesting")
    st.caption("Simple long/cash moving-average crossover backtest using yfinance history.")

    cols = st.columns([1, 1, 1, 1])
    ticker = cols[0].text_input("Backtest ticker", value="MSFT").upper()
    start_date = cols[1].date_input("Start date", value=date.today() - timedelta(days=365 * 5))
    short_window = cols[2].number_input("Short MA", min_value=5, max_value=100, value=20, step=5)
    long_window = cols[3].number_input("Long MA", min_value=20, max_value=250, value=50, step=10)
    starting_cash = st.number_input("Starting cash", min_value=1_000.0, value=100_000.0, step=10_000.0)

    if st.button("Run Backtest", type="primary"):
        try:
            history = get_price_history(ticker, start=start_date)
            results, metrics = moving_average_crossover_backtest(
                history,
                short_window=int(short_window),
                long_window=int(long_window),
                starting_cash=float(starting_cash),
            )
            st.session_state["backtest"] = {"ticker": ticker, "results": results, "metrics": metrics}
            _log(f"Ran moving-average backtest for {ticker}")
        except ValueError as exc:
            st.error(str(exc))

    backtest = st.session_state.get("backtest")
    if not backtest:
        st.info("Run a backtest to compare the crossover strategy with buy and hold.")
        return

    metrics = backtest["metrics"]
    metric_cols = st.columns(5)
    metric_cols[0].metric("Strategy Return", _percent(metrics["total_return"]))
    metric_cols[1].metric("Buy & Hold", _percent(metrics["buy_hold_return"]))
    metric_cols[2].metric("Trades", f"{metrics['number_of_trades']}")
    metric_cols[3].metric("Ending Equity", _money(metrics["ending_equity"]))
    metric_cols[4].metric("Max Drawdown", _percent(metrics["max_drawdown"]))

    results = backtest["results"]
    if isinstance(results, pd.DataFrame) and not results.empty:
        st.plotly_chart(backtest_equity_chart(results, backtest["ticker"]), use_container_width=True)
        st.dataframe(results.tail(20), use_container_width=True, hide_index=True)
    else:
        st.warning("Not enough price history for that backtest configuration.")


def render_paper_trading() -> None:
    st.subheader("Paper Trading")
    st.caption("Paper trading only. No live orders.")

    alpaca_configured = alpaca_ready(
        _secret_value("ALPACA_API_KEY"),
        _secret_value("ALPACA_SECRET_KEY"),
        _secret_value("ALPACA_BASE_URL") or "https://paper-api.alpaca.markets",
    )
    st.info(
        "Alpaca paper credentials detected in Streamlit secrets."
        if alpaca_configured
        else "Add ALPACA_API_KEY, ALPACA_SECRET_KEY, and ALPACA_BASE_URL to Streamlit secrets when ready."
    )

    action_cols = st.columns(3)
    if action_cols[0].button("Check Alpaca Connection"):
        if alpaca_configured:
            st.success("Alpaca paper credentials are configured. Live API calls are intentionally disabled.")
        else:
            st.warning("Missing Alpaca secrets. Add them in Streamlit Community Cloud secrets when ready.")
    if action_cols[1].button("View Paper Account"):
        st.info("Placeholder only. This will show paper account balances after Alpaca API calls are enabled.")
    if action_cols[2].button("Submit Test Paper Order"):
        st.info("Placeholder only. No order was sent to Alpaca.")

    with st.form("position_form", clear_on_submit=True):
        cols = st.columns(6)
        ticker = cols[0].text_input("Ticker")
        side = cols[1].selectbox("Side", ["buy", "sell"])
        quantity = cols[2].number_input("Quantity", min_value=0.0, step=1.0)
        order_type = cols[3].selectbox("Order Type", ["market", "limit"])
        limit_price = cols[4].number_input("Limit Price", min_value=0.0, step=1.0)
        submitted = cols[5].form_submit_button("Simulate")

    if submitted and ticker:
        order = create_simulated_order(
            ticker=ticker,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price if order_type == "limit" else None,
        )
        st.session_state["paper_orders"].append(order.as_dict())
        _add_position(ticker.upper(), "Long" if side == "buy" else "Short", limit_price, quantity)
        _log(f"Simulated {side} order for {ticker.upper()}")

    portfolio = pd.DataFrame(st.session_state["portfolio"])
    orders = pd.DataFrame(st.session_state["paper_orders"])

    st.markdown("### Paper Positions")
    if portfolio.empty:
        st.info("No paper positions yet.")
    else:
        st.dataframe(portfolio, use_container_width=True, hide_index=True)

    st.markdown("### Simulated Orders")
    if orders.empty:
        st.info("No simulated orders yet.")
    else:
        st.dataframe(orders, use_container_width=True, hide_index=True)


def render_portfolio() -> None:
    st.subheader("Paper Portfolio")
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
    st.session_state.setdefault("paper_orders", [])
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


def _percent(value: object) -> str:
    return f"{value:.1%}" if isinstance(value, (int, float)) else "n/a"


def _window_return(history: pd.DataFrame, window: int) -> float | None:
    if history.empty or "Close" not in history:
        return None
    closes = history["Close"].dropna().tail(window)
    if len(closes) < 2 or closes.iloc[0] == 0:
        return None
    return float((closes.iloc[-1] / closes.iloc[0]) - 1)


def _secret_value(name: str) -> str | None:
    try:
        return st.secrets.get(name)
    except Exception:
        return None


def _scanner_classification(score: float) -> str:
    if score >= 70:
        return "Long Watch"
    if score <= 45:
        return "Short Watch"
    return "Avoid / Neutral"


def _scanner_explanation(
    score: float,
    one_month_return: float | None,
    three_month_return: float | None,
) -> str:
    if score >= 70:
        return "Strong recent trend with acceptable volatility."
    if score <= 45:
        return "Weak or choppy trend; candidate for caution."
    if one_month_return is None or three_month_return is None:
        return "Insufficient clean price history; keep neutral."
    if one_month_return > 0 and three_month_return > 0:
        return "Positive trend, but score is not strong enough for long watch."
    return "Mixed signal; wait for a clearer setup."


def _tradingview_url(ticker: str) -> str:
    return f"https://www.tradingview.com/symbols/NASDAQ-{ticker.upper()}/"


def _tradingview_embed(ticker: str) -> str:
    symbol = f"NASDAQ:{ticker.upper()}"
    return f"""
    <div class="tradingview-widget-container" style="height:500px;width:100%">
      <iframe
        src="https://www.tradingview.com/widgetembed/?symbol={symbol}&interval=D&theme=light&style=1&timezone=America%2FNew_York"
        style="height:500px;width:100%;border:0"
        allowtransparency="true"
        scrolling="no">
      </iframe>
    </div>
    """


if __name__ == "__main__":
    main()
