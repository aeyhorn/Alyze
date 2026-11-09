---
name: dev-sync
description: >-
  Gleicht PROJECT_STATUS, PROJECT_GOALS und REQUIREMENTS mit Git ab, damit
  Desktop- und mobile Cloud-Entwicklung denselben Stand sehen. Nutzen beim
  Sitzungsstart, bei einer neuen Anforderung und wenn der Sync-Koordinator
  laufen soll.
---

# Dev-Sync Koordinator

Dieser Lauf ändert keinen Produktcode. Er hält die drei Dokumente mit dem Repo gleich und schiebt das Ergebnis auf `origin`.

Dokumente:

- `bdx-intelligence/docs/PROJECT_STATUS.md`
- `bdx-intelligence/docs/PROJECT_GOALS.md`
- `bdx-intelligence/docs/REQUIREMENTS.md`

Die Kurzpflicht für jede Sitzung steht in `.cursor/rules/dev-sync.mdc`.

## Ablauf

1. `git fetch --all --prune` ausführen.
2. Die drei Dokumente lesen.
3. Den Baum gegen die Dokumente halten:
   - `git status`
   - `git log --oneline origin/main..HEAD`
   - `git branch -r --no-merged origin/main`
   - `gh pr list --state open` (wenn `gh` angemeldet ist)
4. Drift korrigieren, nur in den drei Dokumenten:
   - Behauptungen wie „uncommitted“ oder „nicht gepusht“ an den tatsächlichen Baum anpassen.
   - Erledigte Anforderungen: Zeile behalten, `Status` auf `done` setzen, das verknüpfte Ziel in `PROJECT_GOALS.md` nachziehen.
   - Neue Ziele nur anlegen, wenn eine Anforderung keinem Ziel zugeordnet ist. IDs `G#` nicht wiederverwenden und nicht umbenennen.
5. **Zuletzt aktualisiert:** in `PROJECT_STATUS.md` und **Zuletzt abgeglichen:** in `PROJECT_GOALS.md` auf den aktuellen Zeitpunkt setzen (Datum, Uhrzeit, Zeitzone).
6. Commit nur, wenn sich eine der drei Dateien geändert hat. Nachricht: `docs: reconcile project status and goals`.
7. Push:
   - Liegt die Sitzung auf `main`: Branch `sync/status-YYYYMMDD` anlegen, dort committen, `git push -u origin HEAD`, PR gegen `main` öffnen. Den PR nicht mergen.
   - Liegt die Sitzung schon auf einem Feature-Branch: auf diesem Branch committen und `git push -u origin HEAD`. Keinen zweiten PR öffnen, wenn einer für den Branch existiert.
8. Kurz berichten: aktive Ziele, offene Anforderungen, Branches die `origin/main` voraus sind, alles was noch nicht auf `origin` liegt.

## Grenzen

- Kein Produktcode, keine Tests, keine Workflows in diesem Lauf.
- Kein Force-Push. Kein `.env`. Kein `SL_DRY_RUN=false` in committeten Dateien.
- Anforderungen nicht löschen. Bei einem Merge beide Zeilen behalten.
- Die Übersichtstabelle in `PROJECT_STATUS.md` darf dieser Lauf anfassen. Feature-Sitzungen lassen sie in Ruhe und ändern nur ihren Abschnitt.
