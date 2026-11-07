"""CLI entry-point: report on open production orders and recent events.

Usage examples
--------------
  bdx-collect report           – print open orders from latest PostgreSQL snapshot
  bdx-collect events           – print recent domain events
  bdx-collect diagnose         – one-shot SAP connectivity and query diagnostic
  bdx-collect collect          – run the polling loop (foreground)
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="bdx-collect", help="BDX Intelligence CLI – SAP B1 collector and reporting tool.")
console = Console()
err_console = Console(stderr=True)


def _get_pg_session():
    """Bootstrap PostgreSQL session from environment."""
    from bdx.config import load_postgres_settings
    from bdx.db.postgres import create_pg_engine, make_session_factory
    settings = load_postgres_settings()
    engine = create_pg_engine(settings.postgres_dsn)
    factory = make_session_factory(engine)
    return factory()


@app.command("report")
def report_orders(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (R, L, C, X)"),
    item_code: Optional[str] = typer.Option(None, "--item", "-i", help="Filter by item code"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max rows to display"),
):
    """Print a table of open production orders from the latest stored snapshot."""
    from bdx.logging_config import configure_logging
    from sqlalchemy import func, select
    from bdx.models.events import OrderSnapshot

    configure_logging("WARNING", "console")

    try:
        session = _get_pg_session()
    except Exception as exc:
        err_console.print(f"[red]Cannot connect to PostgreSQL: {exc}[/red]")
        raise typer.Exit(1)

    latest_ts = session.execute(select(func.max(OrderSnapshot.captured_at))).scalar()
    if latest_ts is None:
        console.print("[yellow]No snapshots found. Run 'bdx-collect collect' first.[/yellow]")
        raise typer.Exit(0)

    q = select(OrderSnapshot).where(OrderSnapshot.captured_at == latest_ts)
    if status:
        q = q.where(OrderSnapshot.status == status.upper())
    if item_code:
        q = q.where(OrderSnapshot.item_code == item_code)
    q = q.limit(limit)

    rows = session.execute(q).scalars().all()
    console.print(f"\n[bold]Snapshot at:[/bold] {latest_ts.isoformat()}  |  [bold]Orders:[/bold] {len(rows)}\n")

    table = Table(show_header=True, header_style="bold cyan")
    for col in ["DocEntry", "DocNum", "Status", "ItemCode", "PlannedQty", "CmpltQty", "DueDate", "UpdatedAt"]:
        table.add_column(col)

    status_colors = {"R": "green", "L": "yellow", "C": "dim", "X": "red"}
    for r in rows:
        color = status_colors.get(r.status, "white")
        table.add_row(
            str(r.doc_entry),
            str(r.doc_num),
            f"[{color}]{r.status}[/{color}]",
            r.item_code,
            f"{float(r.planned_qty):.2f}",
            f"{float(r.completed_qty):.2f}",
            r.due_date or "–",
            r.sap_update_date or "–",
        )

    console.print(table)
    session.close()


@app.command("events")
def report_events(
    event_type: Optional[str] = typer.Option(None, "--type", "-t", help="e.g. ORDER_CREATED"),
    source_key: Optional[str] = typer.Option(None, "--key", "-k"),
    limit: int = typer.Option(50, "--limit", "-n"),
):
    """Print recent domain events."""
    from bdx.logging_config import configure_logging
    from sqlalchemy import select
    from bdx.models.events import DomainEvent

    configure_logging("WARNING", "console")

    try:
        session = _get_pg_session()
    except Exception as exc:
        err_console.print(f"[red]Cannot connect to PostgreSQL: {exc}[/red]")
        raise typer.Exit(1)

    q = select(DomainEvent).order_by(DomainEvent.occurred_at.desc())
    if event_type:
        q = q.where(DomainEvent.event_type == event_type.upper())
    if source_key:
        q = q.where(DomainEvent.source_key == source_key)
    q = q.limit(limit)

    rows = session.execute(q).scalars().all()
    console.print(f"\n[bold]Domain Events[/bold] (latest {len(rows)})\n")

    table = Table(show_header=True, header_style="bold magenta")
    for col in ["OccurredAt", "EventType", "SourceKey", "DocNum", "ItemCode", "Payload"]:
        table.add_column(col)

    type_colors = {
        "ORDER_CREATED": "green",
        "ORDER_RELEASED": "cyan",
        "QUANTITY_CHANGED": "yellow",
        "DUE_DATE_CHANGED": "yellow",
        "ORDER_CLOSED": "dim",
    }
    for ev in rows:
        color = type_colors.get(ev.event_type, "white")
        payload_str = str(ev.payload or {})[:60]
        table.add_row(
            ev.occurred_at.strftime("%Y-%m-%d %H:%M:%S"),
            f"[{color}]{ev.event_type}[/{color}]",
            ev.source_key,
            str(ev.doc_num),
            ev.item_code,
            payload_str,
        )

    console.print(table)
    session.close()


@app.command("diagnose")
def diagnose(
    skip_sap: bool = typer.Option(False, "--skip-sap", help="Skip SAP connectivity check"),
):
    """One-shot diagnostic: check SAP and PostgreSQL connectivity, run sample queries."""
    from bdx.logging_config import configure_logging
    configure_logging("INFO", "console")

    console.print("\n[bold blue]BDX Intelligence – Diagnostic Mode[/bold blue]\n")

    # PostgreSQL check
    console.print("[bold]1. PostgreSQL[/bold]")
    try:
        from sqlalchemy import text
        session = _get_pg_session()
        session.execute(text("SELECT 1"))
        console.print("   [green]✓ Connected[/green]")
        from sqlalchemy import select, func
        from bdx.models.events import OrderSnapshot, DomainEvent
        snap_count = session.execute(select(func.count(OrderSnapshot.id))).scalar()
        event_count = session.execute(select(func.count(DomainEvent.id))).scalar()
        console.print(f"   Snapshots: {snap_count}  |  Events: {event_count}")
        session.close()
    except Exception as exc:
        console.print(f"   [red]✗ Failed: {exc}[/red]")

    # SAP check
    if not skip_sap:
        console.print("\n[bold]2. SAP Business One SQL Server[/bold]")
        try:
            from bdx.config import load_sap_settings
            from bdx.db.sap import create_sap_engine, probe_sap_connection
            sap_cfg = load_sap_settings()
            engine = create_sap_engine(sap_cfg)
            ok = probe_sap_connection(engine)
            if ok:
                console.print("   [green]✓ Connected[/green]")
                console.print(f"   Host: {sap_cfg.host}:{sap_cfg.port}  DB: {sap_cfg.name}")
                # Sample query
                with engine.connect() as conn:
                    from bdx.db.queries import fetch_open_orders
                    orders = fetch_open_orders(conn)
                    console.print(f"   Open production orders: {len(orders)}")
            else:
                console.print("   [red]✗ Unreachable[/red]")
        except Exception as exc:
            console.print(f"   [red]✗ Failed: {exc}[/red]")
    else:
        console.print("\n[bold]2. SAP Business One SQL Server[/bold]  [dim]skipped[/dim]")

    console.print("\n[bold]Diagnostic complete.[/bold]\n")


@app.command("collect")
def collect(
    once: bool = typer.Option(False, "--once", help="Run a single cycle then exit"),
):
    """Start the SAP polling collector (runs until SIGTERM/SIGINT)."""
    from bdx.config import load_collector_settings, load_postgres_settings, load_sap_settings
    from bdx.db.postgres import create_pg_engine, make_session_factory
    from bdx.db.sap import create_sap_engine
    from bdx.logging_config import configure_logging
    from bdx.collector.polling import run_once, run_polling_loop

    configure_logging()

    sap_cfg = load_sap_settings()
    sap_engine = create_sap_engine(sap_cfg)
    pg_dsn = load_postgres_settings().postgres_dsn
    pg_engine = create_pg_engine(pg_dsn)
    factory = make_session_factory(pg_engine)
    collector_cfg = load_collector_settings()

    if once:
        orders, events = run_once(sap_engine, factory)
        console.print(f"[green]Cycle complete:[/green] {len(orders)} orders, {len(events)} events")
    else:
        run_polling_loop(sap_engine, factory, collector_cfg)


if __name__ == "__main__":
    app()
