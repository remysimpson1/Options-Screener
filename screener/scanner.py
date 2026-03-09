"""Core scanning logic and unusual activity detection."""

import math
from datetime import datetime
from typing import Any

from screener import config


def compute_est_premium(contract: dict) -> float:
    """Estimated premium = last * volume * 100."""
    last = contract.get("last") or 0.0
    volume = contract.get("volume") or 0
    return float(last) * int(volume) * 100


def compute_sentiment(contract: dict) -> str:
    """Determine sentiment based on where last price sits relative to bid/ask."""
    bid = contract.get("bid") or 0.0
    ask = contract.get("ask") or 0.0
    last = contract.get("last")
    if last is None or ask <= bid:
        return "Neutral"
    mid = (bid + ask) / 2.0
    if last >= mid + (ask - mid) * 0.3:
        return "Bullish"
    elif last <= mid - (mid - bid) * 0.3:
        return "Bearish"
    return "Neutral"


def compute_vol_oi_ratio(contract: dict) -> float:
    volume = contract.get("volume") or 0
    oi = contract.get("open_interest") or 0
    if oi == 0:
        return 0.0
    return float(volume) / float(oi)


def enrich_contracts(contracts: list[dict]) -> list[dict]:
    """Add computed fields to each contract."""
    for c in contracts:
        c["est_premium"] = compute_est_premium(c)
        c["sentiment"] = compute_sentiment(c)
        c["vol_oi_ratio"] = compute_vol_oi_ratio(c)
        c["scan_time"] = datetime.now().strftime("%H:%M:%S")
    return contracts


def detect_unusual(contracts: list[dict]) -> list[dict]:
    """Flag contracts with unusual activity. Sets 'unusual_reasons' list on each."""
    if not contracts:
        return contracts

    # Compute top-1% volume threshold
    volumes = sorted([c.get("volume") or 0 for c in contracts], reverse=True)
    cutoff_idx = max(1, math.ceil(len(volumes) * config.TOP_PERCENT_THRESHOLD))
    top_volume_threshold = volumes[min(cutoff_idx - 1, len(volumes) - 1)]

    for c in contracts:
        reasons: list[str] = []
        vol = c.get("volume") or 0
        oi = c.get("open_interest") or 0
        est_premium = c.get("est_premium", 0.0)
        vol_oi = c.get("vol_oi_ratio", 0.0)

        if oi > 0 and vol_oi >= config.VOL_OI_THRESHOLD:
            reasons.append(f"Vol/OI {vol_oi:.1f}x")
        if est_premium >= config.BIG_PREMIUM_THRESHOLD:
            reasons.append(f"Premium ${est_premium:,.0f}")
        if vol >= top_volume_threshold and top_volume_threshold > 0:
            reasons.append("Top 1% Vol")

        c["is_unusual"] = len(reasons) > 0
        c["unusual_reasons"] = reasons

    return contracts


def sort_by_volume(contracts: list[dict]) -> list[dict]:
    """Sort contracts by volume descending."""
    return sorted(contracts, key=lambda c: c.get("volume") or 0, reverse=True)


def scan_and_analyze(contracts: list[dict]) -> list[dict]:
    """Full pipeline: enrich, detect unusual, sort."""
    contracts = enrich_contracts(contracts)
    contracts = detect_unusual(contracts)
    contracts = sort_by_volume(contracts)
    return contracts


def compute_summary(contracts: list[dict]) -> dict[str, Any]:
    """Compute summary statistics for the dashboard header."""
    ticker_volume: dict[str, int] = {}
    total_call_vol = 0
    total_put_vol = 0
    largest_premium = 0.0
    unusual_count = 0

    for c in contracts:
        sym = c.get("underlying", "???")
        vol = c.get("volume") or 0
        ticker_volume[sym] = ticker_volume.get(sym, 0) + vol

        opt_type = (c.get("option_type") or "").lower()
        if opt_type == "call":
            total_call_vol += vol
        elif opt_type == "put":
            total_put_vol += vol

        est = c.get("est_premium", 0.0)
        if est > largest_premium:
            largest_premium = est

        if c.get("is_unusual"):
            unusual_count += 1

    top_tickers = sorted(ticker_volume.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "top_tickers": top_tickers,
        "total_call_vol": total_call_vol,
        "total_put_vol": total_put_vol,
        "largest_premium": largest_premium,
        "unusual_count": unusual_count,
    }
