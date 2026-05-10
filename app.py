"""AI Long/Short Command Center Streamlit app."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from modules.backtesting import moving_average_crossover_backtest
from modules.alpaca_client import (
    get_connection_status,
    get_paper_account,
    get_paper_orders,
    get_paper_positions,
    submit_paper_order,
)
from modules.charts import backtest_equity_chart, price_volume_chart
from modules.market_data import DEFAULT_IDEAS, get_daily_ideas, get_price_history, get_ticker_snapshot
from modules.memo_agent import generate_investment_memo
from modules.scoring import score_ideas, score_ticker, simple_score
from modules.trade_journal import append_trade_journal, read_trade_journal


SCANNER_UNIVERSE = ["AAPL", "MSFT", "NVDA", "META", "AMZN", "GOOGL", "TSLA"]


st.set_page_config(
    page_title="AI Long/Short Command Center",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)


def main() -> None:
    _init_state()
    inject_command_center_css()
    render_command_header()

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


def inject_command_center_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --cc-bg: #050807;
            --cc-bg-2: #07100d;
            --cc-card: #0d1713;
            --cc-card-2: #101f19;
            --cc-border: #1f3d32;
            --cc-green: #00ff88;
            --cc-green-2: #00d084;
            --cc-muted: #8fa89b;
            --cc-text: #e8fff3;
            --cc-danger: #ff5c7a;
            --cc-amber: #ffc857;
        }

        .stApp {
            background:
                radial-gradient(circle at 18% 0%, rgba(0, 255, 136, 0.08), transparent 28rem),
                radial-gradient(circle at 90% 8%, rgba(0, 208, 132, 0.06), transparent 24rem),
                linear-gradient(180deg, var(--cc-bg-2) 0%, var(--cc-bg) 45%, #030504 100%);
            color: var(--cc-text);
        }

        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 3rem;
            max-width: 1500px;
        }

        h1, h2, h3, h4, h5, h6, p, label, span, div {
            letter-spacing: 0;
        }

        h1, h2, h3 {
            color: var(--cc-text) !important;
        }

        .cc-header {
            border: 1px solid var(--cc-border);
            background: linear-gradient(135deg, rgba(13, 23, 19, 0.96), rgba(5, 8, 7, 0.94));
            border-radius: 8px;
            padding: 18px 20px;
            margin-bottom: 18px;
            box-shadow: 0 0 0 1px rgba(0, 255, 136, 0.05), 0 18px 42px rgba(0, 0, 0, 0.35);
        }

        .cc-header h1 {
            margin: 0;
            font-size: 1.7rem;
            line-height: 1.15;
            color: var(--cc-text);
        }

        .cc-header p {
            margin: 6px 0 14px;
            color: var(--cc-muted);
            font-size: 0.94rem;
        }

        .cc-status-row {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }

        .cc-pill {
            border: 1px solid var(--cc-border);
            color: var(--cc-green);
            background: rgba(0, 255, 136, 0.06);
            border-radius: 999px;
            padding: 5px 10px;
            font-size: 0.78rem;
            font-weight: 700;
        }

        .cc-metric-card {
            min-height: 92px;
            border: 1px solid var(--cc-border);
            border-radius: 8px;
            background: linear-gradient(180deg, rgba(16, 31, 25, 0.98), rgba(9, 16, 13, 0.98));
            padding: 12px 13px;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
        }

        .cc-metric-label {
            color: var(--cc-muted);
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            margin-bottom: 8px;
        }

        .cc-metric-value {
            color: var(--cc-green);
            font-size: 1.22rem;
            line-height: 1.2;
            font-weight: 800;
            overflow-wrap: anywhere;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--cc-border) !important;
            background: rgba(13, 23, 19, 0.9) !important;
            border-radius: 8px !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
        }

        div[data-testid="stMetric"] {
            border: 1px solid var(--cc-border);
            background: var(--cc-card);
            border-radius: 8px;
            padding: 12px;
        }

        div[data-testid="stMetricLabel"] p {
            color: var(--cc-muted) !important;
            font-weight: 700;
        }

        div[data-testid="stMetricValue"] {
            color: var(--cc-green) !important;
        }

        .stButton > button, .stDownloadButton > button, .stLinkButton > a {
            border: 1px solid var(--cc-green-2) !important;
            background: linear-gradient(180deg, rgba(0, 255, 136, 0.18), rgba(0, 208, 132, 0.08)) !important;
            color: var(--cc-text) !important;
            border-radius: 8px !important;
            font-weight: 800 !important;
            min-height: 2.4rem;
            box-shadow: 0 0 18px rgba(0, 255, 136, 0.12);
        }

        .stButton > button:hover, .stLinkButton > a:hover {
            border-color: var(--cc-green) !important;
            color: var(--cc-green) !important;
            box-shadow: 0 0 24px rgba(0, 255, 136, 0.22);
        }

        div[data-baseweb="tab-list"] {
            gap: 6px;
            border-bottom: 1px solid var(--cc-border);
        }

        button[data-baseweb="tab"] {
            background: var(--cc-card) !important;
            border: 1px solid var(--cc-border) !important;
            border-bottom: none !important;
            border-radius: 8px 8px 0 0 !important;
            color: var(--cc-muted) !important;
            font-weight: 800 !important;
            padding: 8px 14px !important;
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            color: var(--cc-green) !important;
            background: #102219 !important;
            box-shadow: inset 0 2px 0 var(--cc-green);
        }

        input, textarea, div[data-baseweb="select"] > div {
            background-color: #08110e !important;
            color: var(--cc-text) !important;
            border-color: var(--cc-border) !important;
            border-radius: 8px !important;
        }

        label, .stCaption, div[data-testid="stCaptionContainer"] {
            color: var(--cc-muted) !important;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--cc-border);
            border-radius: 8px;
            overflow: hidden;
            background: var(--cc-card);
        }

        .stAlert {
            border-radius: 8px;
        }

        hr {
            border-color: var(--cc-border);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_command_header() -> None:
    st.markdown(
        """
        <div class="cc-header">
            <h1>AI Long/Short Command Center</h1>
            <p>Autonomous market research, scoring, backtesting, and paper trading</p>
            <div class="cc-status-row">
                <span class="cc-pill">Market Data: yfinance</span>
                <span class="cc-pill">AI: OpenAI</span>
                <span class="cc-pill">Mode: Paper / Research Only</span>
                <span class="cc-pill">Broker: Alpaca Paper</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(column: object, label: str, value: object) -> None:
    column.markdown(
        f"""
        <div class="cc-metric-card">
            <div class="cc-metric-label">{label}</div>
            <div class="cc-metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
    left, main_col = st.columns([0.9, 2.1], gap="large")

    with left:
        st.markdown("#### Research Control Panel")
        ticker = st.text_input("Ticker", value="MSFT").upper()
        period = st.selectbox("Price history", ["3mo", "6mo", "1y", "2y", "5y"], index=2)
        notes = st.text_area("Analyst notes", placeholder="Catalysts, concerns, variant perception...")
        run_research = st.button("Run Research", type="primary")
        st.markdown("#### TradingView")
        st.link_button("Open Selected Ticker", _tradingview_url(ticker or "MSFT"))

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

        with main_col:
            metric_cols = st.columns(6)
            render_metric_card(metric_cols[0], "Selected Ticker", research["ticker"])
            render_metric_card(metric_cols[1], "Current Price", _money(snapshot.get("price")))
            render_metric_card(metric_cols[2], "Market Cap", _market_cap(snapshot.get("market_cap")))
            render_metric_card(metric_cols[3], "Score", f"{score['total_score']}/100")
            render_metric_card(metric_cols[4], "Direction", score["stance"])
            render_metric_card(metric_cols[5], "Risk Label", _risk_label(score))

            if isinstance(history, pd.DataFrame) and not history.empty:
                st.plotly_chart(price_volume_chart(history, research["ticker"]), use_container_width=True)

        st.markdown("### TradingView Widget")
        tradingview_url = _tradingview_url(research["ticker"])
        components.html(_tradingview_embed(research["ticker"]), height=520, scrolling=False)
        st.link_button("Open on TradingView", tradingview_url)

        with st.container(border=True):
            st.markdown("### AI Investment Memo")
            st.markdown(research["memo"])

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Add To Watchlist"):
                _add_watchlist(research["ticker"], score["stance"], score["total_score"])
        with c2:
            if st.button("Add Paper Position"):
                _add_position(research["ticker"], score["stance"], snapshot.get("price"))
    else:
        with main_col:
            st.info("Run research to load the ticker dashboard, chart stack, TradingView view, and memo.")


def render_daily_scanner() -> None:
    st.subheader("Daily Scanner")
    st.caption("Ranks the core mega-cap universe with simple_score using recent trend and volatility.")

    control_col, result_col = st.columns([0.85, 2.15], gap="large")

    with control_col:
        with st.container(border=True):
            st.markdown("#### Scanner Control Panel")
            st.write("Universe: AAPL, MSFT, NVDA, META, AMZN, GOOGL, TSLA")
            st.write("Signal model: recent trend minus volatility penalty")
            run_scanner = st.button("Run Daily Scanner", type="primary")

    if run_scanner:
        _run_daily_scanner()

    scanner = st.session_state.get("scanner")
    with result_col:
        if isinstance(scanner, pd.DataFrame) and not scanner.empty:
            metric_cols = st.columns(4)
            render_metric_card(metric_cols[0], "Tickers Scanned", len(scanner))
            render_metric_card(metric_cols[1], "Highest Score", _number(scanner["score"].max()))
            render_metric_card(metric_cols[2], "Long Watch", int((scanner["classification"] == "Long Watch").sum()))
            render_metric_card(metric_cols[3], "Short Watch", int((scanner["classification"] == "Short Watch").sum()))
            st.dataframe(scanner, use_container_width=True, hide_index=True)
        else:
            st.info("Run the scanner to rank AAPL, MSFT, NVDA, META, AMZN, GOOGL, and TSLA.")


def render_backtesting() -> None:
    st.subheader("Backtesting")
    st.caption("Simple long/cash moving-average crossover backtest using yfinance history.")

    control_col, chart_col = st.columns([0.85, 2.15], gap="large")

    with control_col:
        with st.container(border=True):
            st.markdown("#### Backtest Controls")
            ticker = st.text_input("Backtest ticker", value="MSFT").upper()
            start_date = st.date_input("Start date", value=date.today() - timedelta(days=365 * 5))
            short_window = st.number_input("Short MA", min_value=5, max_value=100, value=20, step=5)
            long_window = st.number_input("Long MA", min_value=20, max_value=250, value=50, step=10)
            starting_cash = st.number_input("Starting cash", min_value=1_000.0, value=100_000.0, step=10_000.0)
            run_backtest = st.button("Run Backtest", type="primary")

    if run_backtest:
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
        with chart_col:
            st.info("Run a backtest to compare the crossover strategy with buy and hold.")
        return

    metrics = backtest["metrics"]
    with chart_col:
        metric_cols = st.columns(5)
        render_metric_card(metric_cols[0], "Strategy Return", _percent(metrics["total_return"]))
        render_metric_card(metric_cols[1], "Buy & Hold", _percent(metrics["buy_hold_return"]))
        render_metric_card(metric_cols[2], "Trades", metrics["number_of_trades"])
        render_metric_card(metric_cols[3], "Ending Equity", _money(metrics["ending_equity"]))
        render_metric_card(metric_cols[4], "Max Drawdown", _percent(metrics["max_drawdown"]))

        results = backtest["results"]
        if isinstance(results, pd.DataFrame) and not results.empty:
            st.plotly_chart(backtest_equity_chart(results, backtest["ticker"]), use_container_width=True)
            st.dataframe(results.tail(20), use_container_width=True, hide_index=True)
        else:
            st.warning("Not enough price history for that backtest configuration.")


def render_paper_trading() -> None:
    st.subheader("Paper Trading")
    st.caption("Paper trading only. No live orders. This is not investment advice.")

    status = get_connection_status()
    status_cols = st.columns([1, 1, 1])
    render_metric_card(status_cols[0], "Mode", "Paper Only")
    render_metric_card(status_cols[1], "Broker", "Alpaca Paper")
    render_metric_card(status_cols[2], "Connection", "Configured" if status["ok"] else "Setup Needed")
    if status["ok"]:
        st.success(status["message"])
    else:
        st.warning(f"{status['error']} Add Alpaca paper credentials in Streamlit secrets to enable API calls.")

    if st.button("Check Alpaca Connection"):
        account_result = get_paper_account()
        if account_result["ok"]:
            st.success("Connected to Alpaca paper trading.")
        else:
            st.error(account_result["error"])

    account_result = get_paper_account()
    if account_result["ok"]:
        account = account_result["data"]
        account_cols = st.columns(3)
        render_metric_card(account_cols[0], "Paper Account Equity", _money_text(account.get("equity")))
        render_metric_card(account_cols[1], "Cash", _money_text(account.get("cash")))
        render_metric_card(account_cols[2], "Buying Power", _money_text(account.get("buying_power")))
    else:
        st.info("Paper account metrics will appear here after Alpaca paper secrets are configured.")

    left, right = st.columns(2, gap="large")
    with left:
        with st.container(border=True):
            st.markdown("### Current Paper Positions")
            positions_result = get_paper_positions()
            if positions_result["ok"]:
                positions = _select_columns(
                    positions_result["data"],
                    ["symbol", "qty", "side", "market_value", "avg_entry_price", "unrealized_pl"],
                )
                if positions.empty:
                    st.info("No current paper positions.")
                else:
                    st.dataframe(positions, use_container_width=True, hide_index=True)
            else:
                st.info("Paper positions will appear here after a valid Alpaca paper connection is available.")

    with right:
        with st.container(border=True):
            st.markdown("### Recent Paper Orders")
            orders_result = get_paper_orders()
            if orders_result["ok"]:
                orders = _select_columns(
                    orders_result["data"],
                    ["submitted_at", "symbol", "side", "qty", "type", "time_in_force", "status"],
                )
                if orders.empty:
                    st.info("No recent paper orders.")
                else:
                    st.dataframe(orders.head(25), use_container_width=True, hide_index=True)
            else:
                st.info("Recent paper orders will appear here after a valid Alpaca paper connection is available.")

    order_col, journal_col = st.columns([0.9, 1.1], gap="large")
    with order_col:
        with st.container(border=True):
            st.markdown("### Submit Paper Test Order")
            with st.form("paper_order_form", clear_on_submit=True):
                cols = st.columns([1, 1, 1])
                symbol = cols[0].text_input("Symbol", value="AAPL")
                qty = cols[1].number_input("Quantity", min_value=0.0, step=1.0, value=1.0)
                side = cols[2].selectbox("Side", ["buy", "sell"])
                notes = st.text_input("Notes", placeholder="Optional journal note")
                confirmed = st.checkbox("I understand this is a simulated paper trade.")
                submitted = st.form_submit_button("Submit Paper Test Order", type="primary")

        if submitted:
            if not confirmed:
                st.error("Confirm the paper-trading checkbox before submitting.")
                append_trade_journal(
                    symbol=symbol,
                    side=side,
                    qty=qty,
                    order_type="market",
                    status_result="rejected_missing_confirmation",
                    notes=notes,
                )
            else:
                result = submit_paper_order(symbol=symbol, qty=qty, side=side)
                status_result = "submitted" if result["ok"] else f"error: {result['error']}"
                append_trade_journal(
                    symbol=symbol,
                    side=side,
                    qty=qty,
                    order_type="market",
                    status_result=status_result,
                    notes=notes,
                )
                if result["ok"]:
                    st.success(result["message"])
                    st.json(_select_order_fields(result["data"]))
                    _log(f"Submitted Alpaca paper {side} order for {symbol.upper()}")
                else:
                    st.error(result["error"])
                    _log(f"Alpaca paper order failed for {symbol.upper()}")

    with journal_col:
        with st.container(border=True):
            st.markdown("### Trade Journal")
            journal = read_trade_journal(limit=25)
            if journal.empty:
                st.info("No trade journal entries yet. Paper order attempts will be recorded here.")
            else:
                st.dataframe(journal, use_container_width=True, hide_index=True)


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


def _market_cap(value: object) -> str:
    if not isinstance(value, (int, float)):
        return "n/a"
    if value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    return _money(value)


def _risk_label(score: dict[str, object]) -> str:
    risk_score = score.get("risk_score")
    if not isinstance(risk_score, (int, float)):
        return "Unknown"
    if risk_score >= 70:
        return "Low"
    if risk_score >= 45:
        return "Moderate"
    return "High"


def _money_text(value: object) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "n/a"


def _select_columns(records: list[dict[str, object]], columns: list[str]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=columns)
    rows = [{column: record.get(column) for column in columns} for record in records]
    return pd.DataFrame(rows)


def _select_order_fields(order: dict[str, object]) -> dict[str, object]:
    fields = ["id", "submitted_at", "symbol", "side", "qty", "type", "time_in_force", "status"]
    return {field: order.get(field) for field in fields if field in order}


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


def _run_daily_scanner() -> None:
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


def _tradingview_url(ticker: str) -> str:
    return f"https://www.tradingview.com/symbols/NASDAQ-{ticker.upper()}/"


def _tradingview_embed(ticker: str) -> str:
    symbol = f"NASDAQ:{ticker.upper()}"
    return f"""
    <div class="tradingview-widget-container" style="height:500px;width:100%">
      <iframe
        src="https://www.tradingview.com/widgetembed/?symbol={symbol}&interval=D&theme=dark&style=1&timezone=America%2FNew_York"
        style="height:500px;width:100%;border:0"
        allowtransparency="true"
        scrolling="no">
      </iframe>
    </div>
    """


if __name__ == "__main__":
    main()
