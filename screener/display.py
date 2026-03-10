"""Rich TUI layout — CheddarFlow-inspired dark dashboard."""

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from screener import config


def _fmt_dollars(val: float) -> str:
    """Format dollar amounts as $XXK or $X.XM."""
    if val >= 1_000_000:
        return f"${val / 1_000_000:.1f}M"
    if val >= 1_000:
        return f"${val / 1_000:.0f}K"
    return f"${val:,.0f}"


def _make_bar(pct: float, width: int = 20, filled_style: str = "green", empty_style: str = "grey30") -> Text:
    """Build a horizontal progress bar."""
    filled = max(0, min(width, int(width * pct / 100)))
    empty = width - filled
    bar = Text()
    bar.append("█" * filled, style=filled_style)
    bar.append("░" * empty, style=empty_style)
    return bar


def make_banner() -> Panel:
    banner_text = Text()
    banner_text.append("  ╔═══════════════════════════════════════════════════╗\n", style="bold cyan")
    banner_text.append("  ║         OPTIONS  FLOW  SCREENER                  ║\n", style="bold cyan")
    banner_text.append("  ║         CheddarFlow-Style Dashboard              ║\n", style="bold cyan")
    banner_text.append("  ╚═══════════════════════════════════════════════════╝", style="bold cyan")
    return Panel(banner_text, border_style="cyan", padding=(0, 1))


def make_summary_panel(summary: dict) -> Panel:
    """Build the CheddarFlow-style 4-panel summary header."""
    table = Table(box=None, show_header=False, padding=(0, 2), expand=True)
    table.add_column(ratio=1)
    table.add_column(ratio=1)
    table.add_column(ratio=1)
    table.add_column(ratio=1)

    # — Panel 1: Flow Sentiment —
    sentiment = summary.get("sentiment", "Neutral")
    pcr = summary.get("put_call_ratio", 0.0)
    sent_color = "green" if sentiment == "Bullish" else ("red" if sentiment == "Bearish" else "yellow")
    # Sentiment bar: 0..2 range mapped to green/red
    bar_pct = max(0, min(100, (1 - pcr / 2) * 100))  # lower pcr = more bullish
    col1 = Text()
    col1.append("Flow sentiment\n", style="dim")
    col1.append(f"{sentiment}\n", style=f"bold {sent_color}")
    col1.append_text(_make_bar(bar_pct, 24, sent_color, "grey30"))
    col1.append(f"  {pcr:.3f}", style="dim")

    # — Panel 2: Put to Call ratio —
    col2 = Text()
    col2.append("Put to call\n", style="dim")
    col2.append(f"{pcr:.3f}\n", style="bold white")
    # Mini donut approximation with text
    call_pct = summary.get("call_pct", 50)
    put_pct = summary.get("put_pct", 50)
    col2.append(f"Calls {call_pct:.0f}%", style="green")
    col2.append(" / ", style="dim")
    col2.append(f"Puts {put_pct:.0f}%", style="red")

    # — Panel 3: Call flow —
    call_flow = summary.get("call_flow", 0)
    col3 = Text()
    col3.append("Call flow\n", style="dim")
    col3.append(f"{_fmt_dollars(call_flow)}\n", style="bold green")
    col3.append_text(_make_bar(call_pct, 20, "green", "grey30"))
    col3.append(f" {call_pct:.0f}%", style="bold green")

    # — Panel 4: Put flow —
    put_flow = summary.get("put_flow", 0)
    col4 = Text()
    col4.append("Put flow\n", style="dim")
    col4.append(f"{_fmt_dollars(put_flow)}\n", style="bold red")
    col4.append_text(_make_bar(put_pct, 20, "red", "grey30"))
    col4.append(f" {put_pct:.0f}%", style="bold red")

    table.add_row(col1, col2, col3, col4)

    return Panel(
        table,
        border_style="grey30",
        style="on grey7",
        padding=(1, 1),
    )


def make_flow_table(contracts: list[dict], max_rows: int = 50) -> Table:
    """Build the CheddarFlow-style flow feed table."""
    table = Table(
        box=box.SIMPLE,
        show_lines=False,
        padding=(0, 1),
        expand=True,
        header_style="bold grey50",
        row_styles=["on grey7", "on grey11"],
    )
    table.add_column("TIME", width=12, no_wrap=True)
    table.add_column("TICK", width=6, no_wrap=True)
    table.add_column("EXPIRY", width=11, no_wrap=True)
    table.add_column("STRIKE", width=8, justify="right", no_wrap=True)
    table.add_column("C/P", width=5, no_wrap=True)
    table.add_column("SPOT", width=9, justify="right", no_wrap=True)
    table.add_column("SIZE", width=7, justify="right", no_wrap=True)
    table.add_column("PRICE", width=8, justify="right", no_wrap=True)
    table.add_column("PREM", width=9, justify="right", no_wrap=True)
    table.add_column("TYPE", width=7, no_wrap=True)
    table.add_column("VOL", width=8, justify="right", no_wrap=True)
    table.add_column("OI", width=8, justify="right", no_wrap=True)

    for c in contracts[:max_rows]:
        opt_type = (c.get("option_type") or "").lower()
        cp_label = "Calls" if opt_type == "call" else "Puts"
        cp_style = "green" if opt_type == "call" else "red"

        trade_type = c.get("trade_type", "")
        if trade_type == "Sweep":
            type_style = "yellow"
        elif trade_type == "Block":
            type_style = "bright_green"
        elif trade_type == "Split":
            type_style = "bright_red"
        else:
            type_style = "dim"

        strike = c.get("strike") or 0
        spot = c.get("spot") or 0
        volume = c.get("volume") or 0
        oi = c.get("open_interest") or 0
        last = c.get("last") or 0
        prem = c.get("est_premium", 0.0)

        table.add_row(
            f"[dim]{c.get('scan_time', '')}[/]",
            f"[bold yellow]{c.get('underlying', '???')}[/]",
            c.get("expiration_date", "")[:10],
            f"{strike:.1f}" if isinstance(strike, float) else str(strike),
            f"[{cp_style}]{cp_label}[/]",
            f"${spot:,.2f}" if spot else "-",
            f"{volume:,}",
            f"${last:.2f}",
            f"[bold green]{_fmt_dollars(prem)}[/]",
            f"[{type_style}]{trade_type}[/]" if trade_type else "",
            f"{volume:,}",
            f"{oi:,}",
        )

    return table


def make_status_bar(filter_desc: str, countdown: int, total: int) -> Text:
    """Build the bottom status bar."""
    bar = Text()
    bar.append(" Filters: ", style="bold cyan")
    bar.append(filter_desc, style="white")
    bar.append("  │  ", style="grey30")
    bar.append(f"{total} contracts", style="white")
    bar.append("  │  ", style="grey30")
    bar.append(f"Refresh {countdown}s", style="bold green")
    bar.append("  │  ", style="grey30")
    bar.append(" [c]alls [p]uts [a]ll [t]icker [m]in$ [u]nusual [q]uit ", style="dim cyan")
    return bar


def build_layout(
    summary: dict,
    contracts: list[dict],
    filter_desc: str,
    countdown: int,
    show_banner: bool = True,
) -> Layout:
    """Assemble the full CheddarFlow-style dashboard layout."""
    layout = Layout()

    parts = []
    if show_banner:
        parts.append(Layout(make_banner(), name="banner", size=6))

    parts.append(Layout(make_summary_panel(summary), name="summary", size=7))

    flow_panel = Panel(
        make_flow_table(contracts),
        title=f"[bold white]Options Flow[/] [dim]({len(contracts)} contracts)[/]",
        border_style="grey30",
        style="on grey7",
        padding=(0, 0),
    )
    parts.append(Layout(flow_panel, name="flow"))

    status = make_status_bar(filter_desc, countdown, len(contracts))
    parts.append(Layout(Panel(status, style="on grey11", border_style="grey30"), name="status", size=3))

    layout.split_column(*parts)
    return layout
