# Alyze Promise Platform – Vision & Build Path

> **Stand:** 2026-11-08 (UTC+1)  
> **Zielbild:** Brauchbare Fertigungs-Promise-Plattform jetzt → eigenständiges, transparentes Kundenportal mit Einkaufsmaschinen und Vertragsbearbeitung.  
> **Nicht-Ziel (Phase 0–1):** Feature-Sammlung ohne durchgängiges Angebotsobjekt.

---

## 1. Nordstern

**Das System besitzt das Angebot und den Vertrag. Menschen und Maschinen räumen Blocker weg und bestätigen Schwellen.**

Der Kunde sieht dieselbe Wahrheit wie intern: Preisband, Terminband, Konfidenz, offene Blocker, Vertragsstand.  
Einkauf und Kapazität sind keine E-Mail-Ketten, sondern **Maschinen** (automationsfähige Agenten mit Policy und Audit), die im Auftrag des Promise-Objekts arbeiten.

```
Zeichnung / Anfrage
        │
        ▼
┌───────────────────┐     Events      ┌────────────────────┐
│  Perception       │────────────────►│  Offer Engine      │
│  bdx-quoter       │                 │  lebendiges Angebot│
│  (Stückkosten,    │                 │  + Gap Runtime     │
│   Normen, offen)  │                 └─────────┬──────────┘
└───────────────────┘                           │
┌───────────────────┐     Ist-Zeiten            │ Policies
│  Reality          │───────────────────────────┤
│  BDX Intelligence │     Kapazität             ▼
│  (SAP, Maschinen) │                 ┌────────────────────┐
└───────────────────┘                 │  Fulfillment Agents│
                                      │  · Einkaufsmaschine│
                                      │  · Kapazitätsmarkt │
                                      │  · Vertragsmaschine│
                                      └─────────┬──────────┘
                                                │
                         intern Cockpit ←───────┼───────→ Kundenportal
                                                │
                                         Vertrag / PO / FA
```

---

## 2. Produktversprechen (was „brauchbar“ heißt)

Ein Mitarbeiter kann **heute** eine Anfrage anlegen und bekommt:

1. parallele Systemantworten (Material, Kapazität, Kalkulation/Quoter),
2. eine **einzige Lückenliste** statt Ansprechpartner-Ping-Pong,
3. ein **Preis-/Terminband mit Konfidenz**,
4. eine Entscheidung (annehmen / Gegenangebot / ablehnen) mit Audit.

Ein Kunde kann **später** dieselben Fakten sehen und Verträge/Änderungen dort führen — ohne zweite Wahrheit in Outlook.

---

## 3. Kernobjekte (durch alle Phasen stabil)

| Objekt | Bedeutung |
|---|---|
| **Offer** | Lebendiges Angebotsobjekt (nicht Snapshot). Versioniert, event-sourced. |
| **Evidence** | Beleg zu jeder Zahl (Zeichnung, WN, SAP, Maschine, Quoter-Lauf). |
| **Gap** | Typisierter Blocker (`technik`, `einkauf`, `fertigung`, `vertrieb`, `recht`). Arbeit, kein Kommentar. |
| **Promise** | `{preis_band, termin_band, konfidenz, schwelle}` – freigabefähig erst ab Policy. |
| **AgentJob** | Auftrag an eine Maschine (Einkauf, Kapazität, Vertrag) mit Policy, Timeout, Audit. |
| **Contract** | Vom Promise abgeleiteter Vertrag / Änderung / Abruf – gleiche Evidenzkette. |
| **Party** | Kunde, Lieferant, interne Rolle – Identitäten für Portal & Rechte. |

Quoter-`offen[]` und SAP-/Kapazitäts-Warnungen **mappen immer auf Gap**, nie auf lose UI-Hinweise.

---

## 4. Maschinen (Agenten) – klare Rollen

### 4.1 Kalkulationsmaschine (heute: bdx-quoter)
- Liest Datenraum, erkennt Stückkosten/Normen, schreibt Evidence + Gaps.
- Kein Vertragsrecht, kein Kundenlogin.

### 4.2 Reality-Maschine (heute: BDX Intelligence)
- SAP-Bestand/Bestellungen, Maschinenstatus, Ist-Durchsatz.
- Speist Closed-loop-Raten und Kapazitätsangebote.

### 4.3 Einkaufsmaschine (Ziel)
- Für Gaps `einkauf` / Normteile / Fehlmengen: holt Lieferkonditionen (Preis, Termin, MOQ) aus SAP/Lieferanten-API oder strukturierter Anfrage.
- Darf **vorschlagen und reservieren** nach Policy; verbindliche Bestellung erst mit Schwelle/Freigabe.
- Audit: jede Kondition als Evidence am Offer.

### 4.4 Kapazitätsmaschine (Ziel)
- Zellen/Maschinen **bieten** Slots (Fähigkeit, ETA, Risiko) – „bewerben sich“.
- Kein Blindflug: Mensch/Policy bestätigt kritische Belegungen.

### 4.5 Vertragsmaschine (Ziel)
- Erzeugt Vertragsentwurf aus Promise (Positionen, Preisband→Festpreis, Termine, Änderungspunkte).
- Verwaltet Versionen, Freigaben, Kundenannahme, Change Orders.
- Kundenportal = UI auf dieselbe Contract-/Offer-Wahrheit.

---

## 5. Transparenz-Kundenportal (Zielbild)

**Eigenständig** = eigene Auth, Branding, Domain – aber **kein zweites Backend**.  
Portal ist eine Projection der Offer/Contract Engine.

Kunde sieht u. a.:
- Anfragestatus und Konfidenz,
- welche Blocker *ihn* betreffen vs. intern,
- Preis-/Terminband (Policy: was extern sichtbar ist),
- Vertragsentwurf / Annahme / Ablehnung / Änderungswunsch,
- Dokumente mit Evidence (freigegebene Zeichnungen, Bestätigungen).

Kunde sieht **nicht** standardmäßig: interne Margen, Lieferantenkonditionen roh, interne Personalengpässe (außer Policy erlaubt „Terminrisiko“).

---

## 6. Stufenbau – brauchbar jetzt, Vision nicht verraten

### Phase A – Internes Promise-OS (brauchbar)
**Lieferumfang**
- Offer-Objekt + Gap Runtime (persistiert, nicht nur Evaluate-Snapshot)
- Quoter + BDX als Perception/Reality an Offer angebunden
- Cockpit: eine Akte, Lücken als Arbeit, Entscheidung + Audit
- Konfidenz-Formel v0 (regelbasiert)

**Exit-Kriterium:** Vertrieb/AV arbeitet Anfragen *nur noch* über die Akte; Mail nur noch Anhang/Eskalation.

### Phase B – Maschinen nach innen
**Lieferumfang**
- Einkaufsmaschine v1 (SAP offene PO + Fehlmengen → Gap schließen / Bestellvorschlag)
- Kapazitätsmaschine v1 (Idle/Backlog → Slot-Vorschlag)
- Closed-loop: BDX-Istzeiten → Raten-Korrekturvorschläge

**Exit-Kriterium:** >50 % der Einkaufs-/Kapazitäts-Gaps werden ohne Mail-Thread erstgeschlossen.

### Phase C – Vertragsmaschine intern
**Lieferumfang**
- Contract aus Promise, Versionierung, interne Freigabestrecke
- Change Order aus Gap/Scope-Änderung

**Exit-Kriterium:** Angebot→Auftrag ohne Abschrift in Word als führendes System.

### Phase D – Kundenportal (eigenständig, transparent)
**Lieferumfang**
- Separates Portal (Auth, Rechte, Branding)
- Read-Modell + Aktionen: annehmen, rückfragen, Vertrag zeichnen, Dokumente
- Gleiche Offer/Contract-IDs, Event-Sync

**Exit-Kriterium:** Pilotkunde führt Klärung und Annahme im Portal; interne Akte spiegelt 1:1.

### Phase E – Autonomie unter Policy
**Lieferumfang**
- Einkaufsmaschine darf innerhalb Limits bestellen
- Kapazitätsmaschine darf Standardslots binden
- Portal zeigt Live-Konfidenz und Blocker-Ownership

---

## 7. Architektur-Invarianten (damit die Vision hält)

1. **Ein Offer pro Anfrage** – Versionen statt Parallel-Wahrheiten.  
2. **Alles Material ist Event** – Quoter-Lauf, SAP-Delta, Gap geschlossen, Vertrag angenommen.  
3. **Gaps sind typisiert und besitzbar** – sonst wieder Mail.  
4. **Portal ist Projection** – keine eigene Kalkulationslogik.  
5. **Maschinen haben Policy + Audit** – keine stille Magie.  
6. **SAP bleibt System of Record für Bestand/FA/Bestellung**, Offer Engine für Promise/Vertrag/Kundensicht.  
7. **Secrets nie im Chat/Portal-Logs** – Credentials nur Env/Secret Store.

---

## 8. Mapping auf den heutigen Code

| Baustein heute | Rolle in der Vision |
|---|---|
| `bdx-quoter` (:8020) | Kalkulationsmaschine / Perception |
| `bdx-intelligence` Q2P | Keimzelle Offer/Gap (noch Snapshot) → ausbauen zur Offer Engine |
| `order_state` / `machine_state` | Reality-Feed |
| PR Quoter-Adapter | Pricing-Domain-Anbindung Phase A |
| Kundenportal | Phase D – neues Deployable, gleiches Event-Backend |

**Nächster Bau-Schritt (nach Vision-Freigabe):** Offer + Gap als First-Class Tabellen/API (weg vom reinen `promise_snapshot`), Gap-Typen + Owner, Recompute-Hook wenn Quoter/BDX Events liefern.

---

## 9. Entscheidungen, die Alexander treffen muss

| Nr | Entscheidung | Empfehlung |
|---|---|---|
| V-1 | Nordstern freigeben (System besitzt Promise/Vertrag)? | Ja |
| V-2 | Phase A Scope: nur intern, kein Kundenlogin? | Ja |
| V-3 | Erstes Pilot-Kundensegment für Phase D? | Ein Stammkunde mit Wiederholteilen |
| V-4 | Einkaufsmaschine: nur vorschlagen oder ab Limit bestellen? | Phase B vorschlagen, Phase E Limits |
| V-5 | Vertragsrecht/Templates wer liefert? | Intern + Legal-Review vor Phase C/D |

---

## 10. Erfolgsmetriken

- Time-to-first-promise (Anfrage → erstes Band)
- Time-to-firm-offer (Konfidenz ≥ Schwelle)
- Anteil Gaps geschlossen ohne Mail-Thread
- Quote-win-rate / Nacharbeitsquote nach Auftrag
- Portal: Anteil Annahmen ohne Telefon/Mail (Phase D+)
