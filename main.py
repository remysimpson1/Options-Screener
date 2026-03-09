#!/usr/bin/env python3
"""Options Flow Screener — Entry point."""

import asyncio
import sys
import threading
import time

from rich.console import Console
from rich.live import Live

from screener import config
from screener.api import fetch_all_chains
from screener.scanner import scan_and_analyze, compute_summary
from screener.filters import FilterState, apply_filters
from screener.display import build_layout

console = Console()

# Shared state
filter_state = FilterState()
all_contracts: list[dict] = []
filtered_contracts: list[dict] = []
summary: dict = {}
countdown: int = config.REFRESH_INTERVAL
running = True
needs_refresh = True


def input_listener():
    """Background thread that reads single keypresses for filter controls."""
    global running, needs_refresh
    import tty
    import termios

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while running:
            ch = sys.stdin.read(1)
            if ch == "q":
                running = False
                break
            elif ch == "c":
                filter_state.option_type = "call"
                needs_refresh = True
            elif ch == "p":
                filter_state.option_type = "put"
                needs_refresh = True
            elif ch == "a":
                filter_state.reset()
                needs_refresh = True
            elif ch == "u":
                filter_state.unusual_only = not filter_state.unusual_only
                needs_refresh = True
            elif ch == "t":
                # Restore terminal for text input
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                console.print("\n[cyan]Enter ticker symbol (or blank to clear):[/] ", end="")
                sym = input().strip().upper()
                filter_state.ticker = sym if sym else None
                needs_refresh = True
                tty.setcbreak(fd)
            elif ch == "m":
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                console.print("\n[cyan]Enter minimum premium $ (or 0 to clear):[/] ", end="")
                try:
                    val = float(input().strip().replace(",", "").replace("$", ""))
                except ValueError:
                    val = 0.0
                filter_state.min_premium = val
                needs_refresh = True
                tty.setcbreak(fd)
    except Exception:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


async def fetch_data():
    """Fetch and process all option chains."""
    global all_contracts, summary
    console.print("[dim]Scanning options chains...[/]")
    raw = await fetch_all_chains(config.WATCHLIST)
    all_contracts = scan_and_analyze(raw)
    summary = compute_summary(all_contracts)

def apply_current_filters():
    """Apply filters to the current contract set."""
    global filtered_contracts
    filtered_contracts = apply_filters(all_contracts, filter_state)

def main():
    global countdown, running, needs_refresh, filtered_contracts

    console.clear()

    # Show startup banner
    from screener.display import make_banner
    console.print(make_banner())
    console.print("[bold cyan]Starting Options Flow Screener...[/]\n")
    console.print(f"[dim]Watchlist: {', '.join(config.WATCHLIST)}[/]")
    console.print(f"[dim]Refresh interval: {config.REFRESH_INTERVAL}s[/]")
    console.print(f"[dim]Data source: Yahoo Finance (delayed)[/]")
    console.print()

    # Initial data fetch
    try:
        asyncio.run(fetch_data())
    except Exception as e:
        console.print(f"[bold red]API Error:[/] {e}")
        console.print("[dim]Check your network connection. yfinance requires internet access.[/]")
        sys.exit(1)

    apply_current_filters()

    if not all_contracts:
        console.print("[yellow]No option contracts found. The market may be closed or the API returned no data.[/]")
        console.print("[dim]Continuing with empty feed — will retry on next refresh cycle.[/]\n")

    # Start keyboard listener
    listener = threading.Thread(target=input_listener, daemon=True)
    listener.start()

    countdown = config.REFRESH_INTERVAL

    try:
        with Live(
            build_layout(summary, filtered_contracts, filter_state.description(), countdown),
            console=console,
            refresh_per_second=2,
            screen=True,
        ) as live:
            last_tick = time.time()

            while running:
                now = time.time()
                elapsed = now - last_tick

                if elapsed >= 1.0:
                    countdown -= int(elapsed)
                    last_tick = now

                    if countdown <= 0:
                        try:
                            asyncio.run(fetch_data())
                        except Exception:
                            pass  # keep showing stale data on transient errors
                        countdown = config.REFRESH_INTERVAL
                        needs_refresh = True

                if needs_refresh:
                    apply_current_filters()
                    needs_refresh = False

                live.update(
                    build_layout(
                        summary,
                        filtered_contracts,
                        filter_state.description(),
                        max(countdown, 0),
                        show_banner=False,
                    )
                )
                time.sleep(0.5)

    except KeyboardInterrupt:
        pass
    finally:
        running = False
        console.print("\n[bold cyan]Options Flow Screener stopped.[/]")


if __name__ == "__main__":
    main()
