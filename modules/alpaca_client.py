"""Paper-only Alpaca client helpers.

All functions in this module are intentionally restricted to Alpaca paper
trading. Live trading URLs are rejected before a client is created.
"""

from __future__ import annotations

from typing import Any

import streamlit as st
from alpaca.common.enums import Sort
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, QueryOrderStatus, TimeInForce
from alpaca.trading.requests import GetOrdersRequest, MarketOrderRequest


PAPER_BASE_URL = "https://paper-api.alpaca.markets"


def get_paper_account() -> dict[str, Any]:
    client_result = _paper_client()
    if not client_result["ok"]:
        return client_result

    try:
        account = client_result["client"].get_account()
        return {"ok": True, "data": _to_public_dict(account)}
    except Exception as exc:
        return _error(f"Could not retrieve Alpaca paper account: {exc}")


def get_paper_positions() -> dict[str, Any]:
    client_result = _paper_client()
    if not client_result["ok"]:
        return client_result

    try:
        positions = client_result["client"].get_all_positions()
        return {"ok": True, "data": [_to_public_dict(position) for position in positions]}
    except Exception as exc:
        return _error(f"Could not retrieve Alpaca paper positions: {exc}")


def get_paper_orders() -> dict[str, Any]:
    client_result = _paper_client()
    if not client_result["ok"]:
        return client_result

    try:
        request = GetOrdersRequest(status=QueryOrderStatus.ALL, limit=25, direction=Sort.DESC)
        orders = client_result["client"].get_orders(filter=request)
        return {"ok": True, "data": [_to_public_dict(order) for order in orders]}
    except Exception as exc:
        return _error(f"Could not retrieve Alpaca paper orders: {exc}")


def submit_paper_order(
    symbol: str,
    qty: float,
    side: str,
    order_type: str = "market",
    time_in_force: str = "day",
) -> dict[str, Any]:
    """Submit a paper-only order to Alpaca.

    This deliberately supports market orders only for Build 3. Keeping the first
    connected order path narrow makes the safety boundary obvious.
    """

    client_result = _paper_client()
    if not client_result["ok"]:
        return client_result

    clean_symbol = symbol.strip().upper()
    if not clean_symbol:
        return _error("Symbol is required.")
    if qty <= 0:
        return _error("Quantity must be greater than zero.")
    if side not in {"buy", "sell"}:
        return _error("Side must be buy or sell.")
    if order_type != "market":
        return _error("Only market paper orders are supported in Build 3.")

    try:
        order_data = MarketOrderRequest(
            symbol=clean_symbol,
            qty=qty,
            side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
            time_in_force=_time_in_force(time_in_force),
        )
        order = client_result["client"].submit_order(order_data=order_data)
        return {"ok": True, "data": _to_public_dict(order), "message": "Paper order submitted."}
    except Exception as exc:
        return _error(f"Could not submit Alpaca paper order: {exc}")


def get_connection_status() -> dict[str, Any]:
    config = _read_config()
    if not config["ok"]:
        return config
    return {"ok": True, "message": "Alpaca paper credentials are configured."}


def _paper_client() -> dict[str, Any]:
    config = _read_config()
    if not config["ok"]:
        return config

    return {
        "ok": True,
        "client": TradingClient(
            api_key=config["api_key"],
            secret_key=config["secret_key"],
            paper=True,
            url_override=config["base_url"],
        ),
    }


def _read_config() -> dict[str, Any]:
    api_key = _secret("ALPACA_API_KEY")
    secret_key = _secret("ALPACA_SECRET_KEY")
    base_url = (_secret("ALPACA_BASE_URL") or PAPER_BASE_URL).rstrip("/")

    missing = [
        name
        for name, value in {
            "ALPACA_API_KEY": api_key,
            "ALPACA_SECRET_KEY": secret_key,
        }.items()
        if not value
    ]
    if missing:
        return _error(f"Missing Streamlit secrets: {', '.join(missing)}.")

    if base_url != PAPER_BASE_URL:
        return _error(
            "Blocked Alpaca connection. This app only supports the paper trading URL: "
            f"{PAPER_BASE_URL}."
        )

    return {"ok": True, "api_key": api_key, "secret_key": secret_key, "base_url": base_url}


def _secret(name: str) -> str | None:
    try:
        value = st.secrets.get(name)
        return str(value) if value else None
    except Exception:
        return None


def _time_in_force(value: str) -> TimeInForce:
    normalized = value.lower()
    if normalized == "day":
        return TimeInForce.DAY
    if normalized == "gtc":
        return TimeInForce.GTC
    return TimeInForce.DAY


def _to_public_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        data = value.model_dump(mode="json")
    elif hasattr(value, "dict"):
        data = value.dict()
    else:
        data = dict(value) if isinstance(value, dict) else vars(value)

    return {key: item for key, item in data.items() if "key" not in key.lower() and "secret" not in key.lower()}


def _error(message: str) -> dict[str, Any]:
    return {"ok": False, "error": message}
