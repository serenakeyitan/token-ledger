"""token-ledger CLI — manage AI token grants and capacity contracts."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Optional

import click

from .models import Entry, EntryType
from . import store, display


# ── Helpers ───────────────────────────────────────────────────────────


def _load_or_die(config_dir: Path) -> list[Entry]:
    return store.load(config_dir)


def _parse_date(ctx, param, value) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise click.BadParameter("use YYYY-MM-DD format")


def _parse_tokens(value: str) -> int:
    """Accept '2M', '500K', '1000000', etc."""
    v = value.strip().upper()
    if v.endswith("M"):
        return int(float(v[:-1]) * 1_000_000)
    if v.endswith("K"):
        return int(float(v[:-1]) * 1_000)
    return int(v)


# ── Root ──────────────────────────────────────────────────────────────


@click.group()
@click.option(
    "--dir",
    "config_dir",
    default=None,
    envvar="TOKEN_LEDGER_DIR",
    help="Override config directory (default: ~/.config/token-ledger)",
)
@click.pass_context
def main(ctx: click.Context, config_dir: Optional[str]) -> None:
    """Track AI token grants, capacity contracts, and burn rate across providers.

    \b
    Quickstart:
      token-ledger add openai-yc --provider openai --type grant --total 2M --expires 2026-12-01
      token-ledger status
      token-ledger use openai-yc 250000
    """
    ctx.ensure_object(dict)
    ctx.obj["config_dir"] = Path(config_dir).expanduser() if config_dir else store.DEFAULT_CONFIG_DIR


# ── status ────────────────────────────────────────────────────────────


@main.command()
@click.option("--window", default=30, show_default=True, help="Burn-rate window in days")
@click.pass_context
def status(ctx: click.Context, window: int) -> None:
    """Show all grants and contracts with burn rate and runway."""
    entries = _load_or_die(ctx.obj["config_dir"])
    display.status_table(entries, window_days=window)


# ── add ───────────────────────────────────────────────────────────────


@main.command()
@click.argument("id")
@click.option("--provider", required=True, help="Provider name: openai, anthropic, google, ...")
@click.option(
    "--type", "entry_type",
    type=click.Choice([t.value for t in EntryType], case_sensitive=False),
    default="grant",
    show_default=True,
    help="Entry type",
)
@click.option("--total", required=True, help="Total tokens: 2M, 500K, 1000000")
@click.option("--label", default="", help="Human-readable label")
@click.option("--expires", callback=_parse_date, default=None, help="Expiry date YYYY-MM-DD")
@click.option("--monthly-limit", default=0, help="Monthly token limit (for subscriptions/contracts)")
@click.option("--notes", default="", help="Free-form notes")
@click.pass_context
def add(
    ctx: click.Context,
    id: str,
    provider: str,
    entry_type: str,
    total: str,
    label: str,
    expires: Optional[date],
    monthly_limit: int,
    notes: str,
) -> None:
    """Add a new grant or contract.

    \b
    Examples:
      token-ledger add openai-yc --provider openai --type grant --total 2M --expires 2026-12-01 --label "YC S26 batch"
      token-ledger add anthropic-startup --provider anthropic --type grant --total 500K --expires 2026-09-01
      token-ledger add google-free --provider google --type prepaid --total 1M
      token-ledger add openai-capacity --provider openai --type contract --total 0 --monthly-limit 10M --expires 2027-05-01
    """
    config_dir = ctx.obj["config_dir"]

    existing = store.get(id, config_dir)
    if existing:
        if not click.confirm(f"Entry '{id}' already exists. Overwrite?"):
            raise click.Abort()

    try:
        total_tokens = _parse_tokens(total)
    except (ValueError, AttributeError):
        raise click.BadParameter(f"Cannot parse token count: {total!r}", param_hint="--total")

    entry = Entry(
        id=id,
        provider=provider.lower(),
        type=EntryType(entry_type),
        total_tokens=total_tokens,
        label=label,
        expires=expires,
        monthly_limit=monthly_limit,
        notes=notes,
    )
    store.upsert(entry, config_dir)
    display.console.print(f"[green]✓[/green] Added [bold cyan]{id}[/bold cyan]")
    display.entry_detail(entry)


# ── use ───────────────────────────────────────────────────────────────


@main.command()
@click.argument("id")
@click.argument("tokens")
@click.option("--set", "set_value", is_flag=True, help="Set used_tokens absolutely instead of adding")
@click.pass_context
def use(ctx: click.Context, id: str, tokens: str, set_value: bool) -> None:
    """Record token usage against an entry.

    \b
    Examples:
      token-ledger use openai-yc 250000        # add 250K used
      token-ledger use openai-yc 1.5M          # add 1.5M used
      token-ledger use openai-yc 3M --set      # set total used to 3M
    """
    config_dir = ctx.obj["config_dir"]
    entry = store.get(id, config_dir)
    if not entry:
        display.console.print(f"[red]Error:[/red] entry '{id}' not found. Run [bold]token-ledger list[/bold] to see IDs.")
        sys.exit(1)

    try:
        n = _parse_tokens(tokens)
    except (ValueError, AttributeError):
        raise click.BadParameter(f"Cannot parse token count: {tokens!r}")

    if set_value:
        entry.used_tokens = n
    else:
        entry.used_tokens += n

    store.upsert(entry, config_dir)

    action = "Set" if set_value else "Added"
    display.console.print(
        f"[green]✓[/green] {action} [bold]{display._fmt_tokens(n)}[/bold] tokens on "
        f"[bold cyan]{id}[/bold cyan]  "
        f"(total used: {display._fmt_tokens(entry.used_tokens)})"
    )


# ── info ──────────────────────────────────────────────────────────────


@main.command()
@click.argument("id")
@click.option("--window", default=30, show_default=True, help="Burn-rate window in days")
@click.pass_context
def info(ctx: click.Context, id: str, window: int) -> None:
    """Show detailed info for a single entry."""
    entry = store.get(id, ctx.obj["config_dir"])
    if not entry:
        display.console.print(f"[red]Error:[/red] entry '{id}' not found.")
        sys.exit(1)
    display.entry_detail(entry, window_days=window)


# ── list ──────────────────────────────────────────────────────────────


@main.command("list")
@click.pass_context
def list_cmd(ctx: click.Context) -> None:
    """List all entry IDs."""
    entries = _load_or_die(ctx.obj["config_dir"])
    if not entries:
        display.console.print("[dim]No entries.[/dim]")
        return
    for e in sorted(entries, key=lambda x: (x.provider, x.id)):
        emoji = display.PROVIDER_EMOJI.get(e.provider.lower(), "⚪")
        display.console.print(f"  {emoji} [bold cyan]{e.id}[/bold cyan]  [dim]{e.label}[/dim]")


# ── remove ────────────────────────────────────────────────────────────


@main.command()
@click.argument("id")
@click.option("--yes", is_flag=True, help="Skip confirmation")
@click.pass_context
def remove(ctx: click.Context, id: str, yes: bool) -> None:
    """Remove an entry from the ledger."""
    if not yes:
        if not click.confirm(f"Remove '{id}'?"):
            raise click.Abort()
    if store.remove(id, ctx.obj["config_dir"]):
        display.console.print(f"[green]✓[/green] Removed [bold cyan]{id}[/bold cyan]")
    else:
        display.console.print(f"[red]Error:[/red] entry '{id}' not found.")
        sys.exit(1)


# ── edit ──────────────────────────────────────────────────────────────


@main.command()
@click.argument("id")
@click.option("--label", default=None, help="Update label")
@click.option("--expires", callback=_parse_date, default=None, help="Update expiry YYYY-MM-DD")
@click.option("--notes", default=None, help="Update notes")
@click.option("--total", default=None, help="Update total tokens")
@click.pass_context
def edit(
    ctx: click.Context,
    id: str,
    label: Optional[str],
    expires: Optional[date],
    notes: Optional[str],
    total: Optional[str],
) -> None:
    """Update fields on an existing entry."""
    config_dir = ctx.obj["config_dir"]
    entry = store.get(id, config_dir)
    if not entry:
        display.console.print(f"[red]Error:[/red] entry '{id}' not found.")
        sys.exit(1)

    if label is not None:
        entry.label = label
    if expires is not None:
        entry.expires = expires
    if notes is not None:
        entry.notes = notes
    if total is not None:
        try:
            entry.total_tokens = _parse_tokens(total)
        except (ValueError, AttributeError):
            raise click.BadParameter(f"Cannot parse token count: {total!r}", param_hint="--total")

    store.upsert(entry, config_dir)
    display.console.print(f"[green]✓[/green] Updated [bold cyan]{id}[/bold cyan]")
    display.entry_detail(entry)
