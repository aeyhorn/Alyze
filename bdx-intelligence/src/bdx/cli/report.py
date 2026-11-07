"""CLI entry-point: report on production orders, machines and recent events.

Usage examples
--------------
  bdx-collect report           – print open orders from the current state table
  bdx-collect events           – print recent domain events
  bdx-collect machines         – print current machine state (from PostgreSQL)
  bdx-collect runs             – print recent collector runs
  bdx-collect diagnose         – one-shot connectivity diagnostic (PG, SAP, XMSK, SCADA, MQTT)
  bdx-collect collect          – run the polling loop (SAP + machines, foreground)
  bdx-collect collect --once   – single SAP cycle (use --full to force a full reload)
  bdx-collect machines --live  – one machine cycle against the XMSK feed
"""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="bdx-collect", help="BDX Intelligence CLI – SAP B1 collector and reporting tool.")
console = Console()
err_console = Console(stderr=True)

_STATUS_COLORS = {"P": "cyan", "R": "green", "L": "dim", "C": "red"}


def _get_pg_factory():
    from bdx.config import load_postgres_settings
    from bdx.db.postgres import create_pg_engine, make_session_factory

    settings = load_postgres_settings()
    engine = create_pg_engine(settings.postgres_dsn)
    return make_session_factory(engine)


def _get_pg_session():
    """Bootstrap PostgreSQL session from environment."""
    return _get_pg_factory()()


def _session_or_exit():
    try:
        return _get_pg_session()
    except Exception as exc:
        err_console.print(f"[red]Cannot connect to PostgreSQL: {exc}[/red]")
        raise typer.Exit(1)


@app.command("report")
def report_orders(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by SAP status (P, R, L, C)"),
    all_orders: bool = typer.Option(False, "--all", "-a", help="Include closed/cancelled orders"),
    item_code: Optional[str] = typer.Option(None, "--item", "-i", help="Filter by item code"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max rows to display"),
):
    """Print a table of production orders from the current state table (open by default)."""
    from sqlalchemy import func, select

    from bdx.logging_config import configure_logging
    from bdx.models.events import OrderState
    from bdx.models.sap import OPEN_STATUSES, STATUS_LABELS

    configure_logging("WARNING", "console")
    session = _session_or_exit()

    latest_ts = session.execute(select(func.max(OrderState.captured_at))).scalar()
    if latest_ts is None:
        console.print("[yellow]No order state found. Run 'bdx-collect collect --once' first.[/yellow]")
        raise typer.Exit(0)

    q = select(OrderState)
    if status:
        q = q.where(OrderState.status == status.upper())
    elif not all_orders:
        q = q.where(OrderState.status.in_(OPEN_STATUSES))
    if item_code:
        q = q.where(OrderState.item_code == item_code)
    total = session.execute(select(func.count()).select_from(q.subquery())).scalar()
    rows = session.execute(q.order_by(OrderState.doc_num.desc()).limit(limit)).scalars().all()

    console.print(f"\n[bold]State as of:[/bold] {latest_ts.isoformat()}  |  [bold]Orders:[/bold] {total} (showing {len(rows)})\n")

    table = Table(show_header=True, header_style="bold cyan")
    for col in ["DocEntry", "DocNum", "Status", "ItemCode", "PlannedQty", "CmpltQty", "DueDate", "SAP-Upd", "Changed"]:
        table.add_column(col)

    for r in rows:
        color = _STATUS_COLORS.get(r.status, "white")
        table.add_row(
            str(r.doc_entry),
            str(r.doc_num),
            f"[{color}]{r.status} {STATUS_LABELS.get(r.status, '')}[/{color}]",
            r.item_code,
            f"{float(r.planned_qty):.2f}",
            f"{float(r.completed_qty):.2f}",
            r.due_date or "–",
            r.sap_update_date or "–",
            r.last_changed_at.strftime("%Y-%m-%d %H:%M") if r.last_changed_at else "–",
        )

    console.print(table)
    session.close()


@app.command("events")
def report_events(
    event_type: Optional[str] = typer.Option(None, "--type", "-t", help="e.g. ORDER_CREATED, MACHINE_STATE_CHANGED"),
    source_key: Optional[str] = typer.Option(None, "--key", "-k"),
    machine_id: Optional[str] = typer.Option(None, "--machine", "-m"),
    limit: int = typer.Option(50, "--limit", "-n"),
):
    """Print recent domain events."""
    from sqlalchemy import select

    from bdx.logging_config import configure_logging
    from bdx.models.events import DomainEvent

    configure_logging("WARNING", "console")
    session = _session_or_exit()

    q = select(DomainEvent).order_by(DomainEvent.occurred_at.desc(), DomainEvent.id.desc())
    if event_type:
        q = q.where(DomainEvent.event_type == event_type.upper())
    if source_key:
        q = q.where(DomainEvent.source_key == source_key)
    if machine_id:
        q = q.where(DomainEvent.machine_id == machine_id)
    q = q.limit(limit)

    rows = session.execute(q).scalars().all()
    console.print(f"\n[bold]Domain Events[/bold] (latest {len(rows)})\n")

    table = Table(show_header=True, header_style="bold magenta")
    for col in ["OccurredAt", "EventType", "Source", "DocNum", "ItemCode", "Payload"]:
        table.add_column(col)

    type_colors = {
        "ORDER_CREATED": "green",
        "ORDER_RELEASED": "cyan",
        "ORDER_PARTIAL_COMPLETE": "green",
        "QUANTITY_CHANGED": "yellow",
        "DUE_DATE_CHANGED": "yellow",
        "ORDER_CLOSED": "dim",
        "MACHINE_STATE_CHANGED": "cyan",
        "MACHINE_ORDER_STARTED": "green",
        "MACHINE_ORDER_FINISHED": "yellow",
        "MACHINE_PIECES_REPORTED": "white",
        "MACHINE_OFFLINE": "red",
        "MACHINE_ONLINE": "green",
    }
    for ev in rows:
        et = str(getattr(ev.event_type, "value", ev.event_type))
        color = type_colors.get(et, "white")
        payload_str = str(ev.payload or {})[:70]
        table.add_row(
            ev.occurred_at.strftime("%Y-%m-%d %H:%M:%S"),
            f"[{color}]{et}[/{color}]",
            ev.machine_id or ev.source_key,
            str(ev.doc_num or "–"),
            ev.item_code or "–",
            payload_str,
        )

    console.print(table)
    session.close()


@app.command("machines")
def report_machines(
    live: bool = typer.Option(False, "--live", help="Run one machine cycle against the XMSK feed first"),
):
    """Print the current machine state (optionally refreshing it from the feed)."""
    from sqlalchemy import select

    from bdx.logging_config import configure_logging
    from bdx.models.events import MachineState

    configure_logging("WARNING", "console")
    factory = _get_pg_factory()

    if live:
        from bdx.adapters.bde import build_machine_adapter
        from bdx.collector.machines import run_machine_cycle
        from bdx.config import load_machine_settings

        m_cfg = load_machine_settings()
        if not m_cfg.configured:
            err_console.print("[red]MACHINE_ENABLED/MACHINE_XMSK_URL not configured[/red]")
            raise typer.Exit(1)
        statuses, events = run_machine_cycle(build_machine_adapter(m_cfg), factory, m_cfg.offline_after_seconds)
        console.print(f"[green]Machine cycle:[/green] {len(statuses)} machines, {len(events)} events")

    session = factory()
    rows = session.execute(select(MachineState).order_by(MachineState.machine_id)).scalars().all()
    if not rows:
        console.print("[yellow]No machine state yet. Try 'bdx-collect machines --live'.[/yellow]")
        raise typer.Exit(0)

    table = Table(show_header=True, header_style="bold cyan")
    for col in ["Machine", "Online", "State", "Exec", "Order", "SAP", "Part", "NC", "Pieces", "F/S/R %", "LastSeen"]:
        table.add_column(col)
    state_colors = {"running": "green", "idle": "yellow", "setup": "cyan", "fault": "red", "off": "dim"}
    for m in rows:
        c = state_colors.get(m.state or "", "white")
        table.add_row(
            m.machine_id,
            "[green]yes[/green]" if m.online else "[red]no[/red]",
            f"[{c}]{m.state or '–'}[/{c}]",
            m.exec_state or "–",
            m.order_ref or "–",
            f"{m.sap_doc_entry}/{m.sap_item_code}" if m.sap_doc_entry else "–",
            m.part or "–",
            m.nc_program or "–",
            m.pieces_raw or "–",
            f"{m.feed_override or '–'}/{m.spindle_override or '–'}/{m.rapid_override or '–'}",
            m.last_seen_at.strftime("%Y-%m-%d %H:%M:%S") if m.last_seen_at else "–",
        )
    console.print(table)
    session.close()


@app.command("runs")
def report_runs(limit: int = typer.Option(20, "--limit", "-n")):
    """Print recent collector runs."""
    from sqlalchemy import select

    from bdx.logging_config import configure_logging
    from bdx.models.events import SnapshotRun

    configure_logging("WARNING", "console")
    session = _session_or_exit()
    rows = session.execute(select(SnapshotRun).order_by(SnapshotRun.started_at.desc()).limit(limit)).scalars().all()

    table = Table(show_header=True, header_style="bold cyan")
    for col in ["Started", "Mode", "Since", "Duration", "Read", "Changed", "Events", "Error"]:
        table.add_column(col)
    for r in rows:
        dur = f"{(r.finished_at - r.started_at).total_seconds():.1f}s" if r.finished_at else "running"
        table.add_row(
            r.started_at.strftime("%Y-%m-%d %H:%M:%S"),
            r.mode,
            r.since_date or "–",
            dur,
            str(r.orders_read),
            str(r.orders_changed),
            str(r.events_created),
            f"[red]{(r.error or '')[:60]}[/red]" if r.error else "",
        )
    console.print(table)
    session.close()


@app.command("diagnose")
def diagnose(
    skip_sap: bool = typer.Option(False, "--skip-sap", help="Skip SAP connectivity check"),
):
    """One-shot diagnostic: check PostgreSQL, SAP, machine feed, SCADA/BDE and MQTT."""
    from bdx.logging_config import configure_logging

    configure_logging("WARNING", "console")

    console.print("\n[bold blue]BDX Intelligence – Diagnostic Mode[/bold blue]\n")

    # PostgreSQL check
    console.print("[bold]1. PostgreSQL[/bold]")
    try:
        from sqlalchemy import func, select, text

        from bdx.models.events import DomainEvent, MachineState, OrderSnapshot, OrderState, SnapshotRun

        session = _get_pg_session()
        session.execute(text("SELECT 1"))
        console.print("   [green]✓ Connected[/green]")
        state_count = session.execute(select(func.count()).select_from(OrderState)).scalar()
        snap_count = session.execute(select(func.count(OrderSnapshot.id))).scalar()
        event_count = session.execute(select(func.count(DomainEvent.id))).scalar()
        run_count = session.execute(select(func.count()).select_from(SnapshotRun)).scalar()
        machine_count = session.execute(select(func.count()).select_from(MachineState)).scalar()
        console.print(
            f"   Orders (state): {state_count}  |  History rows: {snap_count}  |  Events: {event_count}"
            f"  |  Runs: {run_count}  |  Machines: {machine_count}"
        )
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
                with engine.connect() as conn:
                    from bdx.db.queries import fetch_open_orders

                    orders = fetch_open_orders(conn)
                    console.print(f"   Open production orders (P/R): {len(orders)}")
            else:
                console.print("   [red]✗ Unreachable[/red]")
        except Exception as exc:
            console.print(f"   [red]✗ Failed: {exc}[/red]")
    else:
        console.print("\n[bold]2. SAP Business One SQL Server[/bold]  [dim]skipped[/dim]")

    # Machine feed
    console.print("\n[bold]3. Machine feed (XMSK)[/bold]")
    try:
        from bdx.adapters.bde import build_machine_adapter
        from bdx.config import load_machine_settings

        m_cfg = load_machine_settings()
        if not m_cfg.configured:
            console.print("   [dim]disabled (MACHINE_ENABLED=false or no MACHINE_XMSK_URL)[/dim]")
        else:
            adapter = build_machine_adapter(m_cfg)
            statuses = adapter.get_all_status()
            if statuses:
                console.print(f"   [green]✓ {len(statuses)} machines[/green] from {m_cfg.xmsk_url}")
                for s in statuses:
                    console.print(f"     - {s.machine_id}: {s.state} exec={s.exec_state} order={s.order_ref or '–'} pieces={s.pieces_raw or '–'}")
            else:
                console.print("   [red]✗ no machines returned[/red]")
    except Exception as exc:
        console.print(f"   [red]✗ Failed: {exc}[/red]")

    # BDE / SCADA
    console.print("\n[bold]4. BDE (SCADA telemetry API)[/bold]")
    try:
        from bdx.adapters.bde import build_bde_adapter
        from bdx.config import load_bde_settings

        b_cfg = load_bde_settings()
        if not b_cfg.configured:
            console.print("   [dim]disabled (BDE_ENABLED=false or no BDE_SCADA_BASE_URL)[/dim]")
        else:
            adapter = build_bde_adapter(b_cfg)
            ok = adapter.health_check()
            console.print("   [green]✓ Reachable[/green]" if ok else "   [red]✗ Unreachable[/red]")
    except Exception as exc:
        console.print(f"   [red]✗ Failed: {exc}[/red]")

    # MQTT
    console.print("\n[bold]5. Event publisher (MQTT)[/bold]")
    try:
        from bdx.config import load_mqtt_settings
        from bdx.publish.mqtt import build_publisher

        q_cfg = load_mqtt_settings()
        if not (q_cfg.enabled and q_cfg.host):
            console.print("   [dim]disabled (MQTT_ENABLED=false or no MQTT_HOST)[/dim]")
        else:
            pub = build_publisher(q_cfg)
            ok = pub.health_check()
            console.print(f"   [green]✓ Connected to {q_cfg.host}:{q_cfg.port}[/green]" if ok else "   [red]✗ Unreachable[/red]")
            pub.close()
    except Exception as exc:
        console.print(f"   [red]✗ Failed: {exc}[/red]")

    console.print("\n[bold]Diagnostic complete.[/bold]\n")


@app.command("collect")
def collect(
    once: bool = typer.Option(False, "--once", help="Run a single SAP cycle then exit"),
    full: bool = typer.Option(False, "--full", help="Force a full reload (ignored without --once)"),
    no_machines: bool = typer.Option(False, "--no-machines", help="Disable the machine collector for this run"),
):
    """Start the collector (SAP polling + machine feed; runs until SIGTERM/SIGINT)."""
    from bdx.collector.polling import run_once, run_polling_loop
    from bdx.config import (
        load_collector_settings,
        load_machine_settings,
        load_mqtt_settings,
        load_postgres_settings,
        load_sap_settings,
    )
    from bdx.db.postgres import create_pg_engine, make_session_factory
    from bdx.db.sap import create_sap_engine
    from bdx.logging_config import configure_logging
    from bdx.publish.mqtt import build_publisher

    configure_logging()

    sap_cfg = load_sap_settings()
    sap_engine = create_sap_engine(sap_cfg)
    pg_dsn = load_postgres_settings().postgres_dsn
    pg_engine = create_pg_engine(pg_dsn)
    factory = make_session_factory(pg_engine)
    collector_cfg = load_collector_settings()
    publisher = build_publisher(load_mqtt_settings())

    if once:
        orders, events = run_once(sap_engine, factory, collector_cfg, force_full=full, publisher=publisher)
        console.print(f"[green]Cycle complete:[/green] {len(orders)} orders read, {len(events)} events")
        publisher.close()
        return

    machine_adapter = None
    m_cfg = load_machine_settings()
    if m_cfg.configured and not no_machines:
        from bdx.adapters.bde import build_machine_adapter

        machine_adapter = build_machine_adapter(m_cfg)

    try:
        run_polling_loop(sap_engine, factory, collector_cfg, machine_adapter, m_cfg, publisher)
    finally:
        publisher.close()


@app.command("serve")
def serve(
    host: Optional[str] = typer.Option(None, "--host"),
    port: Optional[int] = typer.Option(None, "--port"),
):
    """Start the REST API + dashboard (uvicorn)."""
    import uvicorn

    from bdx.api.main import create_app
    from bdx.config import load_app_settings

    cfg = load_app_settings()
    uvicorn.run(create_app(), host=host or cfg.api_host, port=port or cfg.api_port, log_level="info")


if __name__ == "__main__":
    app()
