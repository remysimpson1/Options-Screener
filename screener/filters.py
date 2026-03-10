"""Filtering engine for the options flow feed."""

from dataclasses import dataclass

from screener import config


@dataclass
class FilterState:
    """Tracks the current active filters."""
    option_type: str | None = None        # "call", "put", or None (all)
    ticker: str | None = None             # specific ticker or None (all)
    min_premium: float = config.MIN_PREMIUM_DEFAULT  # default $25K like CheddarFlow
    unusual_only: bool = False            # show only unusual activity

    def description(self) -> str:
        parts: list[str] = []
        if self.option_type:
            parts.append(self.option_type.upper() + "S only")
        if self.ticker:
            parts.append(f"Ticker: {self.ticker}")
        if self.min_premium > 0:
            parts.append(f"Min Premium: ${self.min_premium:,.0f}")
        if self.unusual_only:
            parts.append("Unusual Only")
        return " | ".join(parts) if parts else "No filters"

    def reset(self) -> None:
        self.option_type = None
        self.ticker = None
        self.min_premium = config.MIN_PREMIUM_DEFAULT
        self.unusual_only = False


def apply_filters(contracts: list[dict], state: FilterState) -> list[dict]:
    """Apply all active filters to the contract list."""
    result = contracts

    if state.option_type:
        result = [
            c for c in result
            if (c.get("option_type") or "").lower() == state.option_type
        ]

    if state.ticker:
        result = [
            c for c in result
            if (c.get("underlying") or "").upper() == state.ticker.upper()
        ]

    if state.min_premium > 0:
        result = [
            c for c in result
            if c.get("est_premium", 0.0) >= state.min_premium
        ]

    if state.unusual_only:
        result = [c for c in result if c.get("is_unusual")]

    return result
