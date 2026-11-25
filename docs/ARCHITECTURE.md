# GroundPulse: System Architecture and Design Document

Problem statement: NAT-002-OP-099 (National Level Innovation)
Status: Design stage (TRL 2). No functional prototype yet.

## 1. Purpose

GroundPulse turns fragmented disaster field reports into a continuously updated, evidence-linked incident record. It shows authorities what is confirmed, contradicted, stale or unverified, and it never dispatches resources on its own.

## 2. System diagram

See `arch.png` (Architecture_drawing.png in the evidence folder). It shows six pipeline stages from left to right, a PostgreSQL + PostGIS data store below, and a human-review gate before any decision.

## 3. Components

| Layer | Component | Function | Output |
|---|---|---|---|
| L1 | Ingestion | Accepts text, voice notes, photos, GPS-tagged observations and authorised external feeds | Raw report with source, device time and location accuracy |
| L2 | Extraction | Extracts category, place, time, condition and urgency; transcribes voice (Odia and English) | Structured report |
| L3 | Matching | Scores each report against open incidents using distance, time gap, semantic similarity, category and source relationship | Candidate matches with scores; borderline cases to a human |
| L4 | Evidence graph | Links Incident → Claim → Observation → Source → Timestamp → Verification | Independent observations, collapsed forwards, conflicts |
| L5 | State engine | Assigns each attribute a state: supported, stale, contradicted, verification pending or resolved | Current state with freshness and reason |
| L6 | Review | Live map, uncertainty layer, prioritised verification queue, decision history | Human decisions, recorded in the audit log |

## 4. Data flow

1. A responder or citizen submits a report (app, voice, SMS or authorised feed).
2. L2 structures it. L3 checks for matching incidents.
3. High-confidence matches attach to an existing incident as candidates. Borderline and low-confidence matches go to the verification queue.
4. L4 records each claim against its observation and source. Forwards of the same message count as one observation.
5. L5 recalculates each attribute's state using its own freshness rule.
6. L6 shows the operator the state, the evidence behind it, and any unverified areas.
7. Every change and human decision is written to the audit log. No record is overwritten.

## 5. Key rules

- **No automatic dispatch.** Human approval is required for any resource decision.
- **No silent merge.** Incident matches are shown as candidates with scores.
- **Unverified is not safe.** Areas with no recent observation are shown as unverified.
- **Every status is traceable.** Each displayed claim links to its observations and timestamps.
- **Personal data is minimised.** Names and phone numbers are masked by default; access is role-based.

## 6. Technology stack

- Frontend: React / Next.js
- Backend: Python / FastAPI
- Database: PostgreSQL with PostGIS (spatial index)
- AI: NLP, semantic embeddings, speech transcription
- Geospatial: OpenStreetMap and GIS processing
- Hosting: cloud or authorised on-premise

## 7. Design parameters (to be tuned on labelled data)

- Matching weights and thresholds: set on the 300 to 500 labelled report set.
- Freshness decay per attribute: road status decays faster than shelter capacity; rates set with responders.
- Credibility: rises with independent, spatially clustered observations; falls with age and contradiction.

These are design starting values, not measured results.

## 8. Limitations and open items

- No functional prototype exists yet.
- Field validation and user interviews are pending.
- Connectivity fallbacks (SMS and voice) are planned, not built.
- Integration with official systems requires formal agreements and is not assumed.

## 9. Prototype plan (75 days)

Build the six stages in order, with a working demonstration on simulated and public data for one flood scenario, and evaluation against the labelled set. The demonstration is the TRL 3 gate.
