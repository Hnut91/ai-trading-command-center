"""CSV-backed trade journal for paper trading activity."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


JOURNAL_PATH = Path("data/trade_journal.csv")
JOURNAL_COLUMNS = [
    "timestamp",
    "symbol",
    "side",
    "qty",
    "order_type",
    "source",
    "status_result",
    "notes",
]


def append_trade_journal(
    symbol: str,
    side: str,
    qty: float,
    order_type: str,
    status_result: str,
    notes: str = "",
    source: str = "manual_paper_test",
) -> pd.DataFrame:
    """Append one paper-trading event to the local CSV journal."""

    JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": symbol.strip().upper(),
        "side": side,
        "qty": qty,
        "order_type": order_type,
        "source": source,
        "status_result": status_result,
        "notes": notes,
    }

    journal = read_trade_journal()
    journal = pd.concat([journal, pd.DataFrame([row])], ignore_index=True)
    journal.to_csv(JOURNAL_PATH, index=False)
    return journal


def read_trade_journal(limit: int | None = None) -> pd.DataFrame:
    """Read the local paper-trading journal."""

    if not JOURNAL_PATH.exists():
        return pd.DataFrame(columns=JOURNAL_COLUMNS)

    journal = pd.read_csv(JOURNAL_PATH)
    for column in JOURNAL_COLUMNS:
        if column not in journal:
            journal[column] = ""

    journal = journal[JOURNAL_COLUMNS]
    if limit:
        return journal.tail(limit).sort_index(ascending=False)
    return journal
