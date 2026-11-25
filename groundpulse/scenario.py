"""Load a scenario file and replay it through the engine."""
import json
from .engine import Engine


def load_engine(path):
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    eng = Engine(zones=cfg.get("zones", []))
    for step in cfg["steps"]:
        eng.advance(step.get("minutes_before", 5))
        eng.ingest(step["text"], step["category"], step["lat"], step["lon"], step.get("source", "citizen"))
    return eng
