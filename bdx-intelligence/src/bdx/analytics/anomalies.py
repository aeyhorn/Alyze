"""Anomaly detection and recommendation engine (Sprint 005).

The detector compares the latest ``KpiResult`` values against the stored
``MetricThreshold`` rows and upserts ``DetectedAnomaly`` rows:

* If the value crosses the crit threshold → severity "crit".
* If it only crosses the warn threshold → severity "warn".
* If a previously open anomaly no longer breaches either threshold →
  ``resolved_at`` is set (self-healing feedback loop).

Human-readable recommendations are generated from a lookup table of
recommendation templates, enriched with the actual metric values.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from bdx.analytics.kpis import KpiResult
from bdx.analytics.thresholds import get_threshold
from bdx.models.analytics import DetectedAnomaly, MetricThreshold

logger = structlog.get_logger(__name__)


# ── Recommendation templates ──────────────────────────────────────────────────
# Keyed by metric_name; {value}, {threshold}, {dim} are substituted at runtime.

_RECOMMENDATIONS: dict[str, dict[str, str]] = {
    "cycle_time_hours": {
        "warn": (
            "Durchlaufzeit für '{dim}' liegt bei {value:.1f} h (Schwellwert: {threshold:.1f} h). "
            "Prüfen Sie Liegezeiten zwischen Vorgängen und ob Maschinen termingerecht belegt sind."
        ),
        "crit": (
            "Kritisch lange Durchlaufzeit für '{dim}': {value:.1f} h (Grenzwert: {threshold:.1f} h). "
            "Sofortiger Kapazitäts- und Priorisierungscheck empfohlen. "
            "Mögliche Ursachen: Engpass-Maschinen, hohe Rüstzeiten, Materialverzug."
        ),
    },
    "on_time_delivery_rate": {
        "warn": (
            "Termintreue liegt bei {value:.1f} % (Ziel: >{threshold:.1f} %). "
            "Überprüfen Sie Auftragsreihenfolge und Kapazitätsplanung."
        ),
        "crit": (
            "Termintreue kritisch niedrig: {value:.1f} % (Grenzwert: {threshold:.1f} %). "
            "Systematische Terminverschiebungen deuten auf strukturellen Kapazitätsengpass hin. "
            "Eskalation an Fertigungsleitung empfohlen."
        ),
    },
    "backlog_overdue_count": {
        "warn": (
            "{value:.0f} offene Fertigungsaufträge haben ihren Termin überschritten. "
            "Priorisierung der überfälligen Aufträge prüfen."
        ),
        "crit": (
            "Kritischer Rückstand: {value:.0f} Aufträge überfällig. "
            "Kapazitätsaufstockung (Überstunden/Fremdvergabe) und Kundenbenachrichtigung prüfen."
        ),
    },
    "rejection_rate_pct": {
        "warn": (
            "Ausschussquote für '{dim}' erhöht: {value:.2f} % (Schwellwert: {threshold:.2f} %). "
            "Qualitätsprüfung der NC-Programme, Werkzeuge und Materialcharge empfohlen."
        ),
        "crit": (
            "Kritische Ausschussquote für '{dim}': {value:.2f} % (Grenzwert: {threshold:.2f} %). "
            "Fertigung dieses Teils sofort auditieren. Prozessparameter, Werkzeugzustand "
            "und Rohteilqualität überprüfen."
        ),
    },
    "release_to_start_hours": {
        "warn": (
            "Median-Startversatz nach FA-Freigabe liegt bei {value:.1f} h (Schwellwert: {threshold:.1f} h). "
            "Prüfen, ob freigegebene Aufträge zeitnah in die Maschinenbelegung übernommen werden."
        ),
        "crit": (
            "Hoher Startversatz: {value:.1f} h nach FA-Freigabe bis Produktionsstart (Grenzwert: {threshold:.1f} h). "
            "Feinplanung und Maschinenbelegungsregel überprüfen. Engpass in der AV?"
        ),
    },
    "order_change_frequency": {
        "warn": (
            "Hohe Änderungsfrequenz: Ø {value:.1f} Änderungen/FA (Schwellwert: {threshold:.1f}). "
            "Häufige Mengen- und Terminänderungen deuten auf instabile Auftragsplanung hin."
        ),
        "crit": (
            "Kritisch viele Auftragsänderungen: Ø {value:.1f}/FA (Grenzwert: {threshold:.1f}). "
            "Planungsprozess überprüfen. Kundenbedarfe werden möglicherweise zu spät kommuniziert."
        ),
    },
    "machine_utilization_pct": {
        "warn": (
            "Maschinenauslastung '{dim}' bei {value:.1f} % (Ziel: >{threshold:.1f} %). "
            "Prüfen Sie Auftragsplanung und ob Rüstzeiten oder Materialfehler die Laufzeit begrenzen."
        ),
        "crit": (
            "Sehr niedrige Auslastung '{dim}': {value:.1f} % (Grenzwert: {threshold:.1f} %). "
            "Maschine ist überwiegend still - Ursachenanalyse (Stillstand, Wartung, fehlende Aufträge) sofort."
        ),
    },
    "setup_ratio_pct": {
        "warn": (
            "Rüstzeit-Anteil für '{dim}': {value:.1f} % (Schwellwert: {threshold:.1f} %). "
            "Rüstoptimierung (SMED) oder Losgrössen-Anpassung prüfen."
        ),
        "crit": (
            "Kritisch hoher Rüstanteil '{dim}': {value:.1f} % (Grenzwert: {threshold:.1f} %). "
            "Produktionsplanung und NC-Programmvorbereitung analysieren. "
            "Ähnliche Teile zusammenfassen?"
        ),
    },
    "mttr_hours": {
        "warn": (
            "Durchschnittliche Ausfallbehebung '{dim}': {value:.2f} h (Schwellwert: {threshold:.2f} h). "
            "Reaktionszeiten Instandhaltung und Ersatzteilverfügbarkeit prüfen."
        ),
        "crit": (
            "Kritisch lange Stillstandsbehebung '{dim}': {value:.2f} h (Grenzwert: {threshold:.2f} h). "
            "Instandhaltungsprozess und Ersatzteilvorrat sofort überprüfen."
        ),
    },
    "mtbf_hours": {
        "warn": (
            "MTBF für '{dim}' bei {value:.1f} h (Ziel: >{threshold:.1f} h). "
            "Präventive Wartungsintervalle überprüfen."
        ),
        "crit": (
            "Kritisch niedrige MTBF '{dim}': {value:.1f} h (Grenzwert: {threshold:.1f} h). "
            "Maschine benötigt dringende Inspektion. Häufige Ausfälle deuten auf Verschleiss hin."
        ),
    },
    "queue_unstarted_count": {
        "warn": (
            "{value:.0f} freigegebene Aufträge warten seit >8h ohne Produktionsstart. "
            "Feinplanungsrückstand prüfen."
        ),
        "crit": (
            "Kritischer Planungsrückstand: {value:.0f} Aufträge freigegeben, aber nicht gestartet. "
            "Kapazitätssituation und Maschinenbelegung sofort überprüfen."
        ),
    },
    "oee_availability_pct": {
        "warn": (
            "OEE-Verfügbarkeit '{dim}': {value:.1f} % (Ziel: >{threshold:.1f} %). "
            "Ungeplante Stillstände analysieren."
        ),
        "crit": (
            "OEE-Verfügbarkeit kritisch niedrig '{dim}': {value:.1f} % (Grenzwert: {threshold:.1f} %). "
            "Maschine ist häufig außer Betrieb. Wartungsplan und Betriebsdaten sofort prüfen."
        ),
    },
}

_DEFAULT_RECOMMENDATION = {
    "warn": "KPI '{metric}' für '{dim}' liegt bei {value:.3f} (Schwellwert: {threshold:.3f}). Überprüfung empfohlen.",
    "crit": "KPI '{metric}' für '{dim}' liegt kritisch bei {value:.3f} (Grenzwert: {threshold:.3f}). Sofortiger Handlungsbedarf.",
}


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _format_recommendation(metric_name: str, severity: str, value: float, threshold: float, dim: str) -> str:
    templates = _RECOMMENDATIONS.get(metric_name, _DEFAULT_RECOMMENDATION)
    template = templates.get(severity, templates.get("warn", ""))
    return template.format(
        metric=metric_name,
        dim=dim or "global",
        value=value,
        threshold=threshold,
    )


def _is_breach(value: float, threshold: MetricThreshold, level: str) -> bool:
    """Return True if *value* breaches the warn or crit threshold."""
    t = threshold.warn_threshold if level == "warn" else threshold.crit_threshold
    if threshold.higher_is_worse:
        return value > t
    else:
        return value < t


def _compute_severity(value: float, threshold: MetricThreshold) -> str | None:
    """Return 'crit', 'warn', or None based on the value."""
    if _is_breach(value, threshold, "crit"):
        return "crit"
    if _is_breach(value, threshold, "warn"):
        return "warn"
    return None


# ── Public API ────────────────────────────────────────────────────────────────


def detect_and_persist(session: Session, kpi_results: list[KpiResult]) -> tuple[int, int, int]:
    """Compare KPI results against thresholds and upsert DetectedAnomaly rows.

    Returns (new_anomalies, updated_anomalies, resolved_anomalies).
    """
    now = _now_utc()
    new_count = updated_count = resolved_count = 0

    for kpi in kpi_results:
        threshold = get_threshold(session, kpi.metric_name, kpi.dimension, kpi.dimension_value)
        if threshold is None:
            # No threshold defined yet - use global fallback if available
            if kpi.dimension != "global":
                threshold = get_threshold(session, kpi.metric_name, "global", None)
            if threshold is None:
                continue

        severity = _compute_severity(kpi.value, threshold)

        # Look for an existing open anomaly for this metric+dimension
        existing = session.execute(
            select(DetectedAnomaly)
            .where(DetectedAnomaly.metric_name == kpi.metric_name)
            .where(DetectedAnomaly.dimension == kpi.dimension)
            .where(
                DetectedAnomaly.dimension_value == kpi.dimension_value
                if kpi.dimension_value is not None
                else DetectedAnomaly.dimension_value.is_(None)
            )
            .where(DetectedAnomaly.resolved_at.is_(None))
        ).scalars().first()

        if severity is None:
            # No breach - resolve any open anomaly
            if existing:
                existing.resolved_at = now
                existing.last_seen_at = now
                resolved_count += 1
                logger.info(
                    "anomaly.resolved",
                    metric=kpi.metric_name,
                    dim=kpi.dimension_value,
                    value=kpi.value,
                )
            continue

        breach_threshold = (
            threshold.crit_threshold if severity == "crit" else threshold.warn_threshold
        )
        recommendation = _format_recommendation(
            kpi.metric_name, severity, kpi.value, breach_threshold,
            kpi.dimension_value or "global",
        )

        if existing:
            existing.severity = severity
            existing.current_value = kpi.value
            existing.threshold = breach_threshold
            existing.recommendation = recommendation
            existing.last_seen_at = now
            if kpi.extra:
                existing.extra = kpi.extra
            updated_count += 1
        else:
            session.add(DetectedAnomaly(
                anomaly_id=str(uuid.uuid4()),
                metric_name=kpi.metric_name,
                dimension=kpi.dimension,
                dimension_value=kpi.dimension_value,
                severity=severity,
                current_value=kpi.value,
                threshold=breach_threshold,
                recommendation=recommendation,
                first_seen_at=now,
                last_seen_at=now,
                resolved_at=None,
                extra=kpi.extra or {},
            ))
            new_count += 1
            logger.info(
                "anomaly.detected",
                metric=kpi.metric_name,
                dim=kpi.dimension_value,
                severity=severity,
                value=kpi.value,
                threshold=breach_threshold,
            )

    session.commit()
    logger.info(
        "anomaly.run_complete",
        new=new_count,
        updated=updated_count,
        resolved=resolved_count,
    )
    return new_count, updated_count, resolved_count


def get_active_anomalies(session: Session) -> list[DetectedAnomaly]:
    """Return all unresolved anomalies ordered by severity then last_seen_at."""
    return session.execute(
        select(DetectedAnomaly)
        .where(DetectedAnomaly.resolved_at.is_(None))
        .order_by(
            # crit before warn (alphabetically crit < warn, invert)
            DetectedAnomaly.severity,
            DetectedAnomaly.last_seen_at.desc(),
        )
    ).scalars().all()
