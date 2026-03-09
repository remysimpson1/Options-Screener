"""Rich TUI layout and rendering for the Options Flow Screener."""

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from screener import config


def make_banner() -> Panel:
    banner_text = Text()
    banner_text.append("  ╔═══════════════════════════════════════════════════╗\n", style="bold cyan")
    banner_text.append("  ║         OPTIONS  FLOW  SCREENER                  ║\n", style="bold cyan")
    banner_text.append("  ║         Unusual Activity Scanner                 ║\n", style="bold cyan")
    banner_text.append("  ╚═══════════════════════════════════════════════════╝", style="bold cyan")
    return Panel(banner_text, border_style="cyan", padding=(0, 1))


def make_summary_panel(summary: dict) -> Panel:
    """Build the top summary dashboard panel."""
    table = Table(box=None, show_header=False, padding=(0, 2), expand=True)
    table.add_column("Section", ratio=1)
    table.add_column("Section", ratio=1)
    table.add_column("Section", ratio=1)
    table.add_column("Section", ratio=1)

    # Column 1: Top tickers by volume
    top_tickers = summary.get("top_tickers", [])
    ticker_lines = Text()
    ticker_lines.append("Top Tickers by Volume\n", style="bold cyan underline")
    if top_tickers:
        max_vol = top_tickers[0][1] if top_tickers else 1
        for sym, vol in top_tickers:
            bar_len = max(1, int(20 * vol / max_vol)) if max_vol > 0 else 1
            bar = "█" * bar_len
            ticker_lines.append(f"  {sym:<5} ", style="bold white")
            ticker_lines.append(bar, style="green")
            ticker_lines.append(f" {vol:,}\n", style="dim")
    else:
        ticker_lines.append("  No data yet\n", style="dim")

    # Column 2: Call vs Put ratio
    call_vol = summary.get("total_call_vol", 0)
    put_vol = summary.get("total_put_vol", 0)
    total = call_vol + put_vol
    ratio_lines = Text()
    ratio_lines.append("Call vs Put Volume\n", style="bold cyan underline")
    if total > 0:
        call_pct = call_vol / total * 100
        put_pct = put_vol / total * 100
        call_bar = "█" * max(1, int(20 * call_pct / 100))
        put_bar = "█" * max(1, int(20 * put_pct / 100))
        ratio_lines.append(f"  CALLS ", style="bold green")
        ratio_lines.append(call_bar, style="green")
        ratio_lines.append(f" {call_vol:,} ({call_pct:.0f}%)\n", style="dim")
        ratio_lines.append(f"  PUTS  ", style="bold red")
        ratio_lines.append(put_bar, style="red")
        ratio_lines.append(f" {put_vol:,} ({put_pct:.0f}%)\n", style="dim")
        ratio = call_vol / put_vol if put_vol > 0 else float("inf")
        ratio_lines.append(f"  Ratio: {ratio:.2f}\n", style="bold yellow")
    else:
        ratio_lines.append("  No data yet\n", style="dim")

    # Column 3: Largest premium
    largest = summary.get("largest_premium", 0.0)
    premium_lines = Text()
    premium_lines.append("Largest Premium\n", style="bold cyan underline")
    premium_lines.append(f"  ${largest:,.0f}\n", style="bold green" if largest > 0 else "dim")

    # Column 4: Unusual count
    unusual = summary.get("unusual_count", 0)
    unusual_lines = Text()
    unusual_lines.append("Unusual Alerts\n", style="bold cyan underline")
    style = "bold yellow" if unusual > 0 else "dim"
    unusual_lines.append(f"  {unusual} contracts\n", style=style)

    table.add_row(ticker_lines, ratio_lines, premium_lines, unusual_lines)

    return Panel(table, title="[bold cyan]Dashboard Summary[/]", border_style="cyan", padding=(0, 1))


def make_flow_table(contracts: list[dict], max_rows: int = 50) -> Table:
    """Build the scrolling flow feed table."""
    table = Table(
        box=box.SIMPLE_HEAVY,
        show_lines=False,
        padding=(0, 1),
        expand=True,
        header_style="bold cyan",
    )
    table.add_column("Time", style="dim", width=8, no_wrap=True)
    table.add_column("Ticker", width=6, no_wrap=True)
    table.add_column("Exp", width=10, no_wrap=True)
    table.add_column("Strike", width=8, justify="right", no_wrap=True)
    table.add_column("C/P", width=4, no_wrap=True)
    table.add_column("Bid", width=8, justify="right", no_wrap=True)
    table.add_column("Ask", width=8, justify="right", no_wrap=True)
    table.add_column("Last", width=8, justify="right", no_wrap=True)
    table.add_column("Volume", width=9, justify="right", no_wrap=True)
    table.add_column("OI", width=9, justify="right", no_wrap=True)
    table.add_column("IV", width=7, justify="right", no_wrap=True)
    table.add_column("Delta", width=7, justify="right", no_wrap=True)
    table.add_column("Est Prem", width=12, justify="right", no_wrap=True)
    table.add_column("Signal", width=10, no_wrap=True)
    table.add_column("Flags", no_wrap=False)

    for c in contracts[:max_rows]:
        is_unusual = c.get("is_unusual", False)
        opt_type = (c.get("option_type") or "").lower()
        row_style = ""
        if is_unusual:
            row_style = "bold yellow"

        cp_style = "green" if opt_type == "call" else "red"
        cp_label = "C" if opt_type == "call" else "P"

        sentiment = c.get("sentiment", "")
        sent_style = "green" if sentiment == "Bullish" else ("red" if sentiment == "Bearish" else "dim")

        greeks = c.get("greeks") or {}
        iv_val = greeks.get("mid_iv") or greeks.get("smv_vol") or 0.0
        delta_val = greeks.get("delta") or 0.0

        strike = c.get("strike") or 0
        bid = c.get("bid") or 0
        ask = c.get("ask") or 0
        last = c.get("last") or 0
        volume = c.get("volume") or 0
        oi = c.get("open_interest") or 0
        est_prem = c.get("est_premium", 0.0)
        reasons = c.get("unusual_reasons", [])

        table.add_row(
            c.get("scan_time", ""),
            f"[bold]{c.get('underlying', '???')}[/]",
            c.get("expiration_date", "")[:10],
            f"{strike:.1f}" if isinstance(strike, float) else str(strike),
            f"[{cp_style}]{cp_label}[/]",
            f"{bid:.2f}",
            f"{ask:.2f}",
            f"{last:.2f}",
            f"{volume:,}",
            f"{oi:,}",
            f"{iv_val:.0%}" if iv_val else "-",
            f"{delta_val:.2f}" if delta_val else "-",
            f"${est_prem:,.0f}",
            f"[{sent_style}]{sentiment}[/]",
            f"[bold yellow]{', '.join(reasons)}[/]" if reasons else "",
            style=row_style,
        )

    return table


def make_status_bar(filter_desc: str, countdown: int, total: int) -> Text:
    """Build the bottom status bar."""
    bar = Text()
    bar.append(" Filters: ", style="bold cyan")
    bar.append(filter_desc, style="white")
    bar.append("  |  ", style="dim")
    bar.append(f"Showing {total} contracts", style="white")
    bar.append("  |  ", style="dim")
    bar.append(f"Refresh in {countdown}s", style="bold green")
    bar.append("  |  ", style="dim")
    bar.append(" [c]alls [p]uts [a]ll [t]icker [m]in$ [u]nusual [q]uit ", style="dim cyan")
    return bar


def build_layout(
    summary: dict,
    contracts: list[dict],
    filter_desc: str,
    countdown: int,
    show_banner: bool = True,
) -> Layout:
    """Assemble the full dashboard layout."""
    layout = Layout()

    parts = []
    if show_banner:
        parts.append(Layout(make_banner(), name="banner", size=6))

    parts.append(Layout(make_summary_panel(summary), name="summary", size=10))

    flow_panel = Panel(
        make_flow_table(contracts),
        title=f"[bold cyan]Options Flow Feed[/] [dim]({len(contracts)} contracts)[/]",
        border_style="cyan",
        padding=(0, 0),
    )
    parts.append(Layout(flow_panel, name="flow"))

    status = make_status_bar(filter_desc, countdown, len(contracts))
    parts.append(Layout(Panel(status, style="on grey11"), name="status", size=3))

    layout.split_column(*parts)
    return layout
