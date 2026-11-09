# bdx-quoter Deep Link Contract (Promise ↔ Quoter)

> **Entscheidung (Alyze / BDX):** Deep Links sind der gewählte Integrationsweg —
> nicht nur API-Recompute ohne UI-Rückkehr.
>
> **Stand:** 2026-11-09  
> **Verbraucher:** BDX Promise-Akte (`/promise`) + Hybrid-Prozessgräte  
> **Zielsystem:** `bdx-quoter` UI + API (Port 8020)

Dieses Dokument ist zugleich **Spezifikation** und **Implementierungs-Prompt** für
den Quoter. Es kann 1:1 an den Quoter-Agenten / das Quoter-Repo übergeben werden.

---

## 0. Prompt für den Quoter-Agenten (kopierbar)

```text
Kontext: Alyze Promise Platform (BDX Intelligence) öffnet bdx-quoter per Deep Link,
damit Technik/Kalkulation fehlende Inputs in der Prozessgräte klären kann, und
kehrt danach in dieselbe Offer-Akte zurück.

Entscheidung: Deep Link + return_url (nicht nur blinder API-Call).

Bitte implementiere in bdx-quoter:

1) UI-Route die Query-Parameter akzeptiert und den Datenraum öffnet.
2) „Fertig / Zurück zu Promise“-Aktion die auf return_url redirected und vorher
   speichert / Kalkulation aktuell hält.
3) Optional: sichtbaren Kontext (offer_id, gap_id, gap_title) in der UI zeigen.
4) Bestehende API (/api/projekt, /api/run, /api/health) unverändert nutzbar lassen —
   BDX recompute liest nach Rückkehr weiterhin über die API.

Contract: siehe docs/QUOTER_DEEP_LINK.md im Alyze-Repo (dieses Dokument).
Akzeptanzkriterien am Ende des Dokuments.
```

---

## 1. Problem / Ziel

Heute ruft BDX den Quoter nur serverseitig über `datenraum` auf
(`POST /api/run`). Es gibt **keinen** navigierbaren Einstieg aus der Promise-Akte
und keinen Rückweg.

Soll-Zustand:

1. Nutzer sieht in der Prozessgräte einen fehlenden Input (z. B. Prüfplan,
   offene Kalkulationsfrage).
2. Klick **„Im Quoter klären“** öffnet den Quoter mit Kontext.
3. Nutzer hinterlegt technische Details / räumt `offen[]` ab.
4. Klick **„Fertig“** → Redirect zurück zur Promise-Akte.
5. Akte macht `recompute` → Evidence + Gaps aktualisieren sich.

---

## 2. Entscheidung

| Option | Status |
|---|---|
| **A – Deep Link + `return_url`** | **gewählt** |
| B – Nur API-Callback ohne Quoter-UI | verworfen als Primärweg |
| C – Manuell Datenraum pflegen + Recompute | bleibt Fallback |

Deep Link ist Primärweg, weil die Arbeit **im Quoter** stattfindet (Zeichnung,
Normen, Offen-Punkte) und die Promise-Akte nur Ownership + Fortschritt zeigt.

---

## 3. URL-Contract (Quoter UI)

### 3.1 Entry (BDX → Quoter)

BDX baut (Config `QUOTER_UI_URL`, Default = Origin von `QUOTER_BASE_URL`):

```text
{QUOTER_UI_URL}/work?
  datenraum={urlencoded path}
  &offer_id={uuid}
  &gap_id={uuid}
  &gap_title={urlencoded short title}
  &item_code={optional}
  &qty={optional}
  &kunde={optional}
  &return_url={urlencoded absolute or path URL back to Promise}
```

**Empfohlene Quoter-Route:** `/work` (oder Alias `/ui/work`).  
Falls die bestehende UI root-basiert ist: Root darf dieselben Query-Parameter lesen.

### 3.2 Pflicht-Parameter

| Param | Pflicht | Bedeutung |
|---|---|---|
| `datenraum` | ja | Pfad/Identität des Quoter-Datenraums |
| `return_url` | ja | Wohin nach „Fertig“ |
| `offer_id` | ja | Promise-Offer-ID (Korrelation, Anzeige) |
| `gap_id` | nein* | Konkreter Gap, der geklärt werden soll |
| `gap_title` | nein | Anzeige („Prüfplan fehlt“) |
| `item_code` | nein | Material |
| `qty` | nein | Menge |
| `kunde` | nein | wie heutiger API-Param |

\*Ohne `gap_id` = allgemeiner Quoter-Einstieg für den Offer-Datenraum
(alle technischen Offen-Punkte).

### 3.3 Exit (Quoter → BDX)

Beim Speichern + „Fertig / Zurück zu Promise“:

1. Sicherstellen, dass der letzte Stand über die bestehende API lesbar ist
   (`/api/projekt` und/oder letzte `/api/run`-Kalkulation).
2. Redirect:

```text
{return_url}
  ?quoter_return=1
  &offer_id={offer_id}
  &gap_id={gap_id|}
  &quoter_status=saved|cancelled
```

BDX Promise-UI wertet `quoter_return=1` aus → `POST /api/v1/promise/offers/{id}/recompute`
→ Gräte/Gaps refreshen.

### 3.4 Abbruch

„Abbrechen“ / Schließen ohne Speichern:

```text
{return_url}?quoter_return=1&offer_id=…&gap_id=…&quoter_status=cancelled
```

Keine Datenänderung erwartet; BDX zeigt die Akte unverändert.

---

## 4. Beispiel

### Outbound (aus Promise)

```text
http://192.168.82.33:8020/work?
  datenraum=%2Fmnt%2F001%20KUNDEN%2F…%2FWN-4412
  &offer_id=6f2c9a1e-…
  &gap_id=b31e0c44-…
  &gap_title=Pr%C3%BCfplan%20fehlt
  &item_code=WN-4412
  &qty=120
  &return_url=http%3A%2F%2F192.168.82.33%3A8010%2Fpromise%3Foffer%3D6f2c9a1e-…
```

### Return (zurück)

```text
http://192.168.82.33:8010/promise?offer=6f2c9a1e-…
  &quoter_return=1
  &offer_id=6f2c9a1e-…
  &gap_id=b31e0c44-…
  &quoter_status=saved
```

---

## 5. UI-Anforderungen im Quoter

1. **Kontextbanner** oben: Offer-ID (kurz), Gap-Titel, Item, „Zurück zu Promise“.
2. **Datenraum** aus Query öffnen (nicht manuell neu wählen, außer Override).
3. Primäraktion **Fertig / Zurück zu Promise** (sichtbar, nicht versteckt im Menü).
4. Sekundäraktion **Abbrechen** → Return mit `quoter_status=cancelled`.
5. Wenn `datenraum` fehlt/ungültig: Fehlermeldung + Link „Zurück“ über `return_url`.
6. Keine neue Auth für Phase A nötig, wenn Quoter im gleichen Vertrauensnetz wie
   heute läuft — später gleiches Session-/SSO-Thema wie BDX.

---

## 6. API — unverändert, aber Garantien

BDX behält den bestehenden Client (`docs/Q2P_QUOTER.md`):

| Method | Path | Nutzung nach Return |
|---|---|---|
| GET | `/api/health` | Diagnose |
| GET | `/api/projekt?datenraum=` | Cache / Projektstand |
| POST | `/api/run` | frische Kalkulation beim Recompute |

**Garantie nach `quoter_status=saved`:**  
Ein anschließendes `GET /api/projekt` bzw. `POST /api/run` ohne `fresh` Sonderlogik
muss den vom Nutzer gespeicherten Stand sehen (inkl. bereinigter / aktualisierter
`offen[]`).

`offen[]`-Einträge, die erledigt wurden, dürfen nicht mehr erscheinen — BDX mappt
Verschwinden auf Gap-Resolve über Fingerprint/`title`.

---

## 7. BDX-Seite (kurz, zur Koordination)

Nicht Teil der Quoter-Implementierung, aber Vertragspartner:

- Env: `QUOTER_UI_URL` (neu), weiterhin `QUOTER_BASE_URL` für API.
- Promise-UI: Button an Gaps `gap_type` ∈ {`technik`,`kalkulation`} bzw. Inputs
  der Prozessgräte mit `source_agent=quote`.
- Vor dem Öffnen: optional AgentJob `in_progress` markieren.
- Bei Return: Recompute + Toast „Quoter-Stand übernommen“.

---

## 8. Akzeptanzkriterien (Quoter)

- [ ] `GET /work?datenraum=…&offer_id=…&return_url=…` öffnet den Datenraum ohne Extra-Klick.
- [ ] Kontextbanner zeigt mindestens `gap_title` oder `offer_id`.
- [ ] **Fertig** speichert und redirected auf `return_url` inkl. `quoter_return=1&quoter_status=saved&offer_id=…`.
- [ ] **Abbrechen** redirected mit `quoter_status=cancelled`.
- [ ] Nach Save liefert API dem BDX-Client aktualisierte Kalkulation / `offen[]`.
- [ ] Ungültiger `datenraum` → Fehler + Rückweg über `return_url`.
- [ ] Bestehende API-Routen bleiben kompatibel (keine Breaking Changes für `quoter.py`).

---

## 9. Nicht-Ziele (Phase A)

- Kein serverseitiger Callback Quoter→BDX nötig (Deep Link Return reicht).
- Keine Änderung der Kalkulations-Engine.
- Kein Kundenportal-Deep-Link.
- Kein SSO.

---

## 10. Rückfragen an Quoter nur wenn nötig

1. Existiert schon eine UI-Route, die wir als `/work` aliasen können?
2. Ist `datenraum` als Query-String heute schon unterstützt?
3. Welche Absolute Base-URL soll BDX in DEV als `QUOTER_UI_URL` eintragen?
