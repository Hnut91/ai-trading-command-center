"""Paper trading helpers prepared for future Alpaca integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PaperOrder:
    ticker: str
    side: str
    quantity: float
    order_type: str
    limit_price: float | None
    submitted_at: str
    status: str = "simulated"

    def as_dict(self) -> dict[str, object]:
        return {
            "ticker": self.ticker,
            "side": self.side,
            "quantity": self.quantity,
            "order_type": self.order_type,
            "limit_price": self.limit_price,
            "submitted_at": self.submitted_at,
            "status": self.status,
        }


def alpaca_ready(api_key: str | None, secret_key: str | None, base_url: str | None) -> bool:
    """Return whether paper-trading credentials are present without exposing them."""

    return bool(api_key and secret_key and base_url)


def create_simulated_order(
    ticker: str,
    side: str,
    quantity: float,
    order_type: str,
    limit_price: float | None = None,
) -> PaperOrder:
    """Create a simulated paper order. This function never places a real trade."""

    return PaperOrder(
        ticker=ticker.strip().upper(),
        side=side,
        quantity=quantity,
        order_type=order_type,
        limit_price=limit_price,
        submitted_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
