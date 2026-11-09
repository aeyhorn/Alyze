"""Confidence formula v0 for living offers."""
from __future__ import annotations

from typing import Any

from bdx.promise.models import GapStatus


# Domain / gap weights for confidence deduction (sum of open weights → lower score)
_GAP_WEIGHTS: dict[str, float] = {
    "technik": 0.18,
    "einkauf": 0.20,
    "fertigung": 0.15,
    "kalkulation": 0.22,
    "personal": 0.10,
    "vertrieb": 0.08,
    "recht": 0.12,
}

_DOMAIN_OK_BONUS: dict[str, float] = {
    "item": 0.05,
    "material": 0.10,
    "bom": 0.05,
    "capacity": 0.10,
    "pricing": 0.15,
}


def compute_confidence(
    *,
    gaps: list[Any],
    evaluation: dict[str, Any] | None,
) -> float:
    """Return confidence in [0, 1].

    Start at 0.55, add bonuses for OK domains, subtract weighted open gaps.
    """
    score = 0.55
    domains = []
    if evaluation and isinstance(evaluation.get("domains"), list):
        domains = evaluation["domains"]
    for d in domains:
        if not isinstance(d, dict):
            continue
        name = str(d.get("domain") or "")
        status = str(d.get("status") or "")
        if status == "ok":
            score += _DOMAIN_OK_BONUS.get(name, 0.03)
        elif status == "warn":
            score += _DOMAIN_OK_BONUS.get(name, 0.03) * 0.35
        elif status == "bad":
            score -= 0.08

    for g in gaps:
        status = getattr(g, "status", None) or (g.get("status") if isinstance(g, dict) else None)
        if status not in (GapStatus.OPEN.value, GapStatus.IN_PROGRESS.value, "open", "in_progress"):
            continue
        gtype = getattr(g, "gap_type", None) or (g.get("gap_type") if isinstance(g, dict) else "vertrieb")
        score -= _GAP_WEIGHTS.get(str(gtype), 0.1)

    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return round(score, 3)


def price_band_from_evaluation(evaluation: dict[str, Any] | None) -> tuple[float | None, float | None]:
    """Derive a simple price band from pricing domain details."""
    if not evaluation:
        return None, None
    for d in evaluation.get("domains") or []:
        if not isinstance(d, dict) or d.get("domain") != "pricing":
            continue
        details = d.get("details") or {}
        netto = details.get("netto_eur")
        if netto is not None:
            n = float(netto)
            # ±8% band until firm
            return round(n * 0.92, 2), round(n * 1.08, 2)
        prices = details.get("prices") or []
        if prices:
            p = float(prices[0].get("price") or 0)
            if p > 0:
                return round(p * 0.95, 2), round(p * 1.10, 2)
    return None, None


def date_band(
    *,
    requested_date: str | None,
    evaluation: dict[str, Any] | None,
) -> tuple[str | None, str | None]:
    early = None
    if evaluation:
        early = evaluation.get("earliest_hint")
    if not early:
        early = requested_date
    late = requested_date
    if early and requested_date and early > requested_date:
        late = early
    elif early and not late:
        late = early
    return early, late
