# GroundPulse

Evidence-aware incident intelligence for disaster response. Turns fragmented field reports into an evidence-linked incident record, so authorities can see what is confirmed, contradicted, stale or unverified.

**Status: working prototype (v0.1.0), rule-based. Not an AI system yet.**

## What works today
- Ingests text reports with category, GPS, and source.
- Extracts condition and severity with keyword rules (`extract()` in `groundpulse/engine.py`).
- Matches reports to open incidents using distance, time gap and text similarity, with thresholds: attach at 0.6, human review at 0.4.
- Collapses forwards: near-identical reports count as one observation.
- Flags contradictions between independent reports.
- Marks stale incidents using per-category freshness windows.
- Marks zones with no recent report as UNVERIFIED. Never "safe".
- Human queue: attach or reject borderline matches; confirm or reject incidents.
- Audit log of every change and human decision.
- No dispatch function exists. Resources move only on a human decision.

## What is not built yet
- **AI extraction:** the NLP model stage is planned. Current extraction is keyword rules.
- **Voice transcription and image understanding:** not built.
- **Real GIS map:** the zone panel is a list, not a map.
- **Authentication:** the operator name is a placeholder. There is no login.
- **Database:** state is held in memory and resets on restart. PostgreSQL + PostGIS is planned.
- **Field validation:** no user interviews or ground testing have happened.
- **Tuned parameters:** thresholds and freshness windows are design values, not tuned on labelled data.

## Run it

Requires Python 3.9 or newer. No third-party packages.

```bash
# Command-line demo
python -m groundpulse.cli data/demo_scenario.json

# Tests
python -m unittest tests.test_engine -v

# Web prototype
python server.py
# then open http://127.0.0.1:8000 and click "Load demo"
```

## Demo data
`data/demo_scenario.json` contains **simulated** reports for demonstration only. They are not real incident data.

## Tests
11 tests cover: six forwards collapsing to one observation, a later report flipping a road to contradicted, unverified zones, rescue ranking, the absence of any dispatch path, staleness, the human queue, reject/confirm decisions, and forward handling. See `docs/TEST_PLAN.md`.

## Layout
```
groundpulse/      engine, scenario loader, CLI
web/index.html    operator dashboard
server.py         local HTTP server (standard library)
data/             simulated demo scenario and labelling template
tests/            unit tests
docs/             architecture, test plan, flowchart
```

## Design
See `docs/ARCHITECTURE.md` and `docs/workflow_flowchart.png`.

## Licence
Not yet chosen. Add a LICENSE file before making the repository public.
