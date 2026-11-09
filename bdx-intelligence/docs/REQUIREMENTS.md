# BDX Intelligence – Requirements

> **Zuletzt abgeglichen:** 2026-11-09 05:37 (UTC+1)
> **Git-Stand:** `main` `723f794` (2026-11-08)
>
> Auf `main` gibt es keinen nummerierten Anforderungskatalog. Diese Datei legt den Katalog an und lässt ihn leer. Sätze aus Vision, Status oder Code werden hier nicht nachträglich zu Anforderungen umgedeutet.

## Katalog

| ID | Quelle | Aussage | Git-Beleg | Status |
|---|---|---|---|---|
| — | — | Keine Zeile. Auf `723f794` ist keine Anforderungs-ID committet. | — | — |

Nächste freie ID: `R001`.

Eine Zeile kommt erst dazu, wenn ein Commit auf `main` eine prüfbare Anforderung ausdrücklich formuliert (Issue, Spec oder Dokument mit Soll-Satz und Nachweis). Ziele stehen in `PROJECT_GOALS.md` und sind keine Anforderungen.

## Wo der Baum Soll-Sätze schon führt

Diese Stellen bleiben die Quelle. Sie bekommen hier keine ID:

| Thema | Datei | Was dort steht |
|---|---|---|
| SAP-Sicherheit, Event-Namen, Testmuster, Never-Liste | `bdx-intelligence/AGENTS.md` | Harte Arbeitsregeln für Änderungen am Baum |
| Promise-Phasen und Exit-Kriterien | `docs/VISION_PROMISE_PLATFORM.md` | Zielbild und offene Entscheidungen V-1 bis V-5 |
| Quoter-HTTP-Vertrag | `docs/Q2P_QUOTER.md` | Angenommene Pfade, überschreibbar über `QUOTER_*_PATH` |
| Architektur und Env-Variablen | `docs/ARCHITECTURE.md` | Beschreibt den gebauten Stand; Teile davon hinken `main` hinterher (siehe `PROJECT_STATUS.md`) |
| CI-Gates | `.github/workflows/ci.yml` | Pytest-Coverage-Untergrenze 68; Ruff und mypy beratend |

## Bewusst keine Anforderung

- Die DEV-Messwerte vom 2026-11-07 (offene Aufträge, Laufzeiten, Maschinen) sind Beobachtungen, keine Soll-Werte.
- Workflow-Erfolg auf `main` (CI und Deploy zu `723f794`) ist ein Lauf, keine Anforderung.
- Ungemergte Dokument-Branches ändern diesen Katalog nicht.
