"""Core scanning logic, trade-type classification, and unusual activity detection."""

import math
from datetime import datetime
from typing import Any

from screener import config


def compute_est_premium(contract: dict) -> float:
    """Estimated premium = last * volume * 100 (each contract = 100 shares)."""
    last = contract.get("last") or 0.0
    volume = contract.get("volume") or 0
    return float(last) * int(volume) * 100


def classify_trade_type(contract: dict) -> str:
    """Classify option activity as Sweep, Block, or Split.

    Heuristic (we only have snapshot data, not tick-level):
      - Block:  large premium (>$100K) and price near the midpoint
      - Sweep:  high vol/OI and price skewed toward ask (calls) or bid (puts)
      - Split:  everything else with meaningful volume
    """
    bid = contract.get("bid") or 0.0
    ask = contract.get("ask") or 0.0
    last = contract.get("last") or 0.0
    volume = contract.get("volume") or 0
    oi = contract.get("open_interest") or 0
    premium = contract.get("est_premium", 0.0)

    if volume == 0:
        return ""

    spread = ask - bid
    mid = (bid + ask) / 2.0

    # Block: large premium, price near mid
    if premium >= 100_000 and spread > 0:
        distance_from_mid = abs(last - mid) / spread if spread > 0 else 0
        if distance_from_mid <= 0.25:
            return "Block"

    # Sweep: aggressive fill (near ask/bid) with elevated vol relative to OI
    vol_oi = (volume / oi) if oi > 0 else 999.0
    if vol_oi >= 1.5 and spread > 0:
        if last >= mid + spread * 0.15:
            return "Sweep"
        if last <= mid - spread * 0.15:
            return "Sweep"

    # Split: moderate fill near mid
    if premium >= 25_000:
        return "Split"

    return ""


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
        c["trade_type"] = classify_trade_type(c)
        c["scan_time"] = datetime.now().strftime("%I:%M:%S %p")
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


def sort_by_premium(contracts: list[dict]) -> list[dict]:
    """Sort contracts by estimated premium descending."""
    return sorted(contracts, key=lambda c: c.get("est_premium", 0), reverse=True)


def scan_and_analyze(contracts: list[dict]) -> list[dict]:
    """Full pipeline: enrich, detect unusual, sort by premium."""
    contracts = enrich_contracts(contracts)
    contracts = detect_unusual(contracts)
    contracts = sort_by_premium(contracts)
    return contracts


def compute_summary(contracts: list[dict]) -> dict[str, Any]:
    """Compute summary statistics for the CheddarFlow-style header."""
    total_call_vol = 0
    total_put_vol = 0
    total_call_premium = 0.0
    total_put_premium = 0.0

    for c in contracts:
        vol = c.get("volume") or 0
        prem = c.get("est_premium", 0.0)
        opt_type = (c.get("option_type") or "").lower()
        if opt_type == "call":
            total_call_vol += vol
            total_call_premium += prem
        elif opt_type == "put":
            total_put_vol += vol
            total_put_premium += prem

    total_vol = total_call_vol + total_put_vol
    total_premium = total_call_premium + total_put_premium
    put_call_ratio = total_put_vol / total_call_vol if total_call_vol > 0 else 0.0
    call_pct = (total_call_premium / total_premium * 100) if total_premium > 0 else 50
    put_pct = (total_put_premium / total_premium * 100) if total_premium > 0 else 50

    if put_call_ratio < 0.7:
        sentiment = "Bullish"
    elif put_call_ratio > 1.3:
        sentiment = "Bearish"
    else:
        sentiment = "Neutral"

    return {
        "sentiment": sentiment,
        "put_call_ratio": put_call_ratio,
        "total_call_vol": total_call_vol,
        "total_put_vol": total_put_vol,
        "call_flow": total_call_premium,
        "put_flow": total_put_premium,
        "call_pct": call_pct,
        "put_pct": put_pct,
    }
