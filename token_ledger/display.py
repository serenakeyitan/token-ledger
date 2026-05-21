"""Rich-powered display helpers for the CLI."""

from __future__ import annotations


from rich.console import Console
from rich.table import Table
from rich import box
from rich.text import Text

from .models import Entry, EntryType

console = Console()

PROVIDER_EMOJI = {
    "openai": "🟢",
    "anthropic": "🟠",
    "google": "🔵",
    "mistral": "🟣",
    "cohere": "🟡",
}

TYPE_LABEL = {
    EntryType.GRANT: "grant",
    EntryType.CONTRACT: "contract",
    EntryType.PREPAID: "prepaid",
    EntryType.SUBSCRIPTION: "sub",
}

WARN_DAYS = 30       # orange if expiring within this many days
DANGER_DAYS = 7      # red if expiring within this many days
WARN_PCT = 75.0      # orange if used > this %
DANGER_PCT = 90.0    # red if used > this %


def _fmt_tokens(n: int) -> str:
    """Format token count as human-readable (1.2M, 450K, etc.)."""
    if n < 0:
        return "unknown"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def _pct_bar(pct: float, width: int = 10) -> Text:
    """Render a compact text progress bar."""
    filled = int(pct / 100 * width)
    bar = "█" * filled + "░" * (width - filled)
    if pct >= DANGER_PCT:
        style = "bold red"
    elif pct >= WARN_PCT:
        style = "yellow"
    else:
        style = "green"
    return Text(f"{bar} {pct:4.0f}%", style=style)


def _expiry_text(entry: Entry) -> Text:
    dr = entry.days_remaining
    if dr is None:
        return Text("never", style="dim")
    if entry.is_expired:
        return Text("EXPIRED", style="bold red")
    if dr <= DANGER_DAYS:
        return Text(f"{dr}d", style="bold red")
    if dr <= WARN_DAYS:
        return Text(f"{dr}d", style="yellow")
    return Text(f"{dr}d", style="dim")


def _runway_text(entry: Entry, daily_rate: float) -> Text:
    days = entry.days_until_exhausted(daily_rate)
    if days is None:
        return Text("—", style="dim")
    if days == 0:
        return Text("exhausted", style="bold red")
    if days <= DANGER_DAYS:
        return Text(f"{days}d", style="bold red")
    if days <= WARN_DAYS:
        return Text(f"{days}d", style="yellow")
    return Text(f"{days}d", style="green")


def status_table(entries: list[Entry], window_days: int = 30) -> None:
    """Print the main status table."""
    if not entries:
        console.print("[dim]No entries. Run [bold]token-ledger add[/bold] to get started.[/dim]")
        return

    table = Table(
        box=box.SIMPLE_HEAVY,
        show_header=True,
        header_style="bold",
        expand=False,
        padding=(0, 1),
    )
    table.add_column("ID", style="bold cyan", no_wrap=True)
    table.add_column("Provider")
    table.add_column("Type", style="dim")
    table.add_column("Total", justify="right")
    table.add_column("Used", justify="right")
    table.add_column("Remaining", justify="right")
    table.add_column("Burn", justify="right", no_wrap=True)
    table.add_column("Expires", justify="right", no_wrap=True)
    table.add_column("Runway", justify="right", no_wrap=True)

    total_remaining = 0
    total_used = 0

    for e in sorted(entries, key=lambda x: (x.provider, x.id)):
        emoji = PROVIDER_EMOJI.get(e.provider.lower(), "⚪")
        provider_str = f"{emoji} {e.provider}"

        daily = e.burn_rate_days(window_days)
        daily_str = f"{_fmt_tokens(int(daily))}/d" if daily > 0 else "—"

        rem = e.remaining_tokens
        rem_str = _fmt_tokens(rem) if rem >= 0 else "∞"

        if e.total_tokens > 0:
            total_remaining += rem
            total_used += e.used_tokens

        table.add_row(
            e.id,
            provider_str,
            TYPE_LABEL.get(e.type, e.type.value),
            _fmt_tokens(e.total_tokens) if e.total_tokens > 0 else "∞",
            _fmt_tokens(e.used_tokens) if e.used_tokens > 0 else "—",
            rem_str,
            daily_str,
            _expiry_text(e),
            _runway_text(e, daily),
        )

    console.print(table)

    # Summary line
    if total_remaining > 0 or total_used > 0:
        console.print(
            f"  [bold]Total remaining:[/bold] {_fmt_tokens(total_remaining)}  "
            f"[bold]Total used:[/bold] {_fmt_tokens(total_used)}"
        )

    # Expiry warnings
    warnings = [e for e in entries if e.days_remaining is not None and 0 < e.days_remaining <= WARN_DAYS]
    if warnings:
        console.print()
        for e in warnings:
            style = "bold red" if e.days_remaining <= DANGER_DAYS else "yellow"
            console.print(f"  [{style}]⚠ {e.id} expires in {e.days_remaining} days ({e.expires})[/{style}]")


def entry_detail(e: Entry, window_days: int = 30) -> None:
    """Print detailed info for a single entry."""
    console.print(f"\n[bold cyan]{e.id}[/bold cyan]  [dim]{e.label or ''}[/dim]")
    console.print(f"  Provider : {PROVIDER_EMOJI.get(e.provider.lower(), '⚪')} {e.provider}")
    console.print(f"  Type     : {e.type.value}")
    console.print(f"  Total    : {_fmt_tokens(e.total_tokens)}")
    console.print(f"  Used     : {_fmt_tokens(e.used_tokens)}")

    if e.total_tokens > 0:
        console.print(f"  Progress : {_pct_bar(e.pct_used)}")

    console.print(f"  Expires  : {e.expires or 'never'}", end="  ")
    if e.days_remaining is not None:
        console.print(_expiry_text(e))
    else:
        console.print()

    daily = e.burn_rate_days(window_days)
    if daily > 0:
        console.print(f"  Burn rate: {_fmt_tokens(int(daily))}/day  (based on {window_days}d window)")
        runway = e.days_until_exhausted(daily)
        if runway is not None:
            console.print(f"  Runway   : {_runway_text(e, daily)}")

    if e.notes:
        console.print(f"  Notes    : [dim]{e.notes}[/dim]")
    console.print()
