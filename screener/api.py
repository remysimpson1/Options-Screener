"""Tradier API client for fetching quotes, expirations, and option chains."""

import asyncio
import os
from typing import Any

import httpx

from screener import config


def _base_url() -> str:
    if config.USE_SANDBOX:
        return config.BASE_URL_SANDBOX
    return config.BASE_URL_PRODUCTION


def _headers() -> dict[str, str]:
    token = os.environ.get("TRADIER_API_TOKEN", "")
    if not token:
        raise RuntimeError(
            "TRADIER_API_TOKEN not set. Copy .env.example to .env and add your token."
        )
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


async def _get(client: httpx.AsyncClient, path: str, params: dict[str, Any] | None = None) -> dict:
    url = f"{_base_url()}{path}"
    resp = await client.get(url, headers=_headers(), params=params, timeout=15.0)
    resp.raise_for_status()
    return resp.json()


async def get_quotes(client: httpx.AsyncClient, symbols: list[str]) -> list[dict]:
    """Fetch quotes for a list of symbols."""
    if not symbols:
        return []
    data = await _get(client, "/markets/quotes", {"symbols": ",".join(symbols)})
    quotes = data.get("quotes", {}).get("quote", [])
    if isinstance(quotes, dict):
        quotes = [quotes]
    return quotes


async def get_expirations(client: httpx.AsyncClient, symbol: str) -> list[str]:
    """Fetch available option expiration dates for a symbol."""
    try:
        data = await _get(client, "/markets/options/expirations", {"symbol": symbol})
        expirations = data.get("expirations", {})
        if expirations is None:
            return []
        dates = expirations.get("date", [])
        if isinstance(dates, str):
            dates = [dates]
        return dates or []
    except (httpx.HTTPStatusError, httpx.RequestError):
        return []


async def get_option_chain(
    client: httpx.AsyncClient, symbol: str, expiration: str
) -> list[dict]:
    """Fetch the full option chain for a symbol and expiration date."""
    try:
        data = await _get(
            client,
            "/markets/options/chains",
            {"symbol": symbol, "expiration": expiration, "greeks": "true"},
        )
        options = data.get("options", {})
        if options is None:
            return []
        chain = options.get("option", [])
        if isinstance(chain, dict):
            chain = [chain]
        return chain or []
    except (httpx.HTTPStatusError, httpx.RequestError):
        return []


async def fetch_all_chains(symbols: list[str]) -> list[dict]:
    """Fetch option chains for all symbols across their nearest expirations.

    Returns a flat list of option contract dicts, each enriched with a
    'underlying' key for the ticker symbol.
    """
    all_contracts: list[dict] = []

    async with httpx.AsyncClient() as client:
        # Fetch expirations for all symbols concurrently
        exp_tasks = {sym: get_expirations(client, sym) for sym in symbols}
        exp_results: dict[str, list[str]] = {}
        for sym, coro in exp_tasks.items():
            exp_results[sym] = await coro
            await asyncio.sleep(config.REQUEST_DELAY)

        # Fetch chains for nearest expirations
        chain_jobs: list[tuple[str, str]] = []
        for sym in symbols:
            exps = exp_results.get(sym, [])[:config.MAX_EXPIRATIONS]
            for exp in exps:
                chain_jobs.append((sym, exp))

        for sym, exp in chain_jobs:
            contracts = await get_option_chain(client, sym, exp)
            for c in contracts:
                c["underlying"] = sym
            all_contracts.extend(contracts)
            await asyncio.sleep(config.REQUEST_DELAY)

    return all_contracts
