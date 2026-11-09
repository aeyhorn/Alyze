"""Capacity agent – machines bid / propose slots from live machine_state."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from bdx.models.events import MachineState, OrderState
from bdx.models.sap import OPEN_STATUSES
from bdx.promise.agents.base import AgentResult
from bdx.promise.models import Offer

_IDLE = frozenset({"idle", "bereit", "ready", "setup", "ruesten", "rüsten", "auftrag"})


def run_capacity_agent(offer: Offer, *, session: Session) -> AgentResult:
    machines = list(session.scalars(select(MachineState)))
    open_same = list(
        session.scalars(
            select(OrderState).where(
                OrderState.status.in_(tuple(OPEN_STATUSES)),
                OrderState.item_code == offer.item_code,
            )
        )
    )

    online = [m for m in machines if m.online]
    idle = [
        m
        for m in online
        if (m.state or "").lower() in _IDLE
        or (m.exec_state or "").lower() in _IDLE
        or not m.order_ref
    ]
    bids: list[dict[str, Any]] = []
    for m in idle:
        bids.append(
            {
                "machine_id": m.machine_id,
                "state": m.state,
                "eta_hint": "sofort",
                "risk": "low",
                "bid": "accept_if_capable",
            }
        )
    for m in online:
        if m in idle:
            continue
        bids.append(
            {
                "machine_id": m.machine_id,
                "state": m.state,
                "eta_hint": "nach aktuellem Auftrag",
                "risk": "medium",
                "bid": "queue",
            }
        )

    gaps: list[dict[str, Any]] = []
    evidence = [
        {
            "kind": "machine",
            "label": "capacity_snapshot",
            "payload": {
                "online": len(online),
                "idle": len(idle),
                "open_orders_same_item": len(open_same),
                "bids": bids,
            },
        }
    ]

    if not machines:
        gaps.append(
            {
                "gap_type": "fertigung",
                "title": "Keine Maschinenstände – Kapazität manuell disponieren",
                "owner_role": "fertigung",
                "source_agent": "capacity",
            }
        )
    elif not idle:
        gaps.append(
            {
                "gap_type": "fertigung",
                "title": "Keine freie Maschine – Slot gegen Belegung abstimmen",
                "owner_role": "fertigung",
                "source_agent": "capacity",
                "extra": {"bids": bids[:5]},
            }
        )

    return AgentResult(
        ok=True,
        summary=f"Kapazität: {len(idle)} frei / {len(online)} online, {len(bids)} Gebote",
        gaps=gaps,
        evidence=evidence,
        payload={"bids": bids, "idle_machine_ids": [m.machine_id for m in idle]},
        needs_human=bool(gaps),
    )
