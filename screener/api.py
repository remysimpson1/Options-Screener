"""Yahoo Finance client for fetching option chains via yfinance."""

import asyncio
import math
from concurrent.futures import ThreadPoolExecutor

import yfinance as yf

from screener import config

_executor = ThreadPoolExecutor(max_workers=4)


def _safe(val, default=0):
    """Return *default* when *val* is None or NaN."""
    if val is None:
        return default
    try:
        if math.isnan(val):
            return default
    except TypeError:
        pass
    return val


def _fetch_chain_sync(symbol: str) -> list[dict]:
    """Fetch option chains for a single ticker (synchronous).

    Returns a flat list of normalised contract dicts.
    """
    try:
        ticker = yf.Ticker(symbol)
        expirations = ticker.options  # tuple of date strings
    except Exception:
        return []

    if not expirations:
        return []

    contracts: list[dict] = []

    for exp in expirations[: config.MAX_EXPIRATIONS]:
        try:
            chain = ticker.option_chain(exp)
        except Exception:
            continue

        for opt_type, df in [("call", chain.calls), ("put", chain.puts)]:
            for _, row in df.iterrows():
                contracts.append(
                    {
                        "symbol": row.get("contractSymbol", ""),
                        "underlying": symbol,
                        "option_type": opt_type,
                        "expiration_date": exp,
                        "strike": float(_safe(row.get("strike"), 0)),
                        "bid": float(_safe(row.get("bid"), 0)),
                        "ask": float(_safe(row.get("ask"), 0)),
                        "last": float(_safe(row.get("lastPrice"), 0)),
                        "volume": int(_safe(row.get("volume"), 0)),
                        "open_interest": int(_safe(row.get("openInterest"), 0)),
                        "greeks": {
                            "mid_iv": float(_safe(row.get("impliedVolatility"), 0)),
                            "delta": 0.0,
                            "gamma": 0.0,
                            "theta": 0.0,
                            "vega": 0.0,
                        },
                    }
                )

    return contracts


async def fetch_all_chains(symbols: list[str]) -> list[dict]:
    """Fetch option chains for all symbols.

    Returns a flat list of option contract dicts, each with an
    'underlying' key for the ticker symbol.
    """
    loop = asyncio.get_running_loop()
    all_contracts: list[dict] = []

    for sym in symbols:
        contracts = await loop.run_in_executor(_executor, _fetch_chain_sync, sym)
        all_contracts.extend(contracts)
        await asyncio.sleep(config.REQUEST_DELAY)

    return all_contracts
