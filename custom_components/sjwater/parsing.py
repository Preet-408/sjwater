"""Pure helpers for the SJ Water Hub bill / usage spreadsheets (no HA imports)."""
from __future__ import annotations

import csv
import io
from datetime import date, datetime

GALLONS_PER_CCF = 748.052


def _to_date(value: str) -> date | None:
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _to_float(value: str) -> float | None:
    value = (value or "").replace("$", "").replace(",", "").strip()
    try:
        return float(value)
    except ValueError:
        return None


def parse_bills(text: str) -> list[dict]:
    """Parse the Billing History CSV. Returns newest-first [{date, amount}]."""
    rows = []
    for row in csv.DictReader(io.StringIO(text.lstrip("﻿"))):
        d = _to_date(row.get("Bill Date", ""))
        amount = _to_float(row.get("Amount", ""))
        if d is not None and amount is not None:
            rows.append({"date": d, "amount": amount})
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows


def parse_usage(text: str) -> list[dict]:
    """Parse the Usage History CSV. Returns newest-first [{date, days, ccf}]."""
    rows = []
    for row in csv.DictReader(io.StringIO(text.lstrip("﻿"))):
        d = _to_date(row.get("Read Date", ""))
        days = _to_float(row.get("No. Of Days", ""))
        ccf = _to_float(row.get("Usage (CCF)", ""))
        if d is not None and days and ccf is not None:
            rows.append({"date": d, "days": int(days), "ccf": ccf})
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows


def summarize(bills: list[dict], reads: list[dict]) -> dict:
    """Combine bills and meter reads into the values the sensors expose."""
    out: dict = {}
    if bills:
        out["latest_bill"] = bills[0]["amount"]
        out["latest_bill_date"] = bills[0]["date"].isoformat()
        out["bills_last_6"] = round(sum(b["amount"] for b in bills[:6]), 2)
        out["bills_count"] = len(bills)
    if reads:
        r = reads[0]
        out["last_read_ccf"] = r["ccf"]
        out["last_read_date"] = r["date"].isoformat()
        out["last_read_days"] = r["days"]
        out["gallons_per_day"] = round(r["ccf"] * GALLONS_PER_CCF / r["days"], 1)
    if bills and reads:
        # Pair the newest bill with the meter read closest to its date (<= 10 days).
        bill = bills[0]
        nearest = min(reads, key=lambda r: abs((r["date"] - bill["date"]).days))
        if abs((nearest["date"] - bill["date"]).days) <= 10 and nearest["ccf"] > 0:
            out["cost_per_ccf"] = round(bill["amount"] / nearest["ccf"], 2)
    return out
