"""GroundPulse rule-based incident engine (prototype).

Stage mapping to the proposal:
  1 Ingestion          -> Engine.ingest(): text, category, GPS, source
  2 Extraction         -> extract(): keyword rules (NOT an AI/NLP model yet)
  3 Matching           -> Engine.score_match(): distance, time, text similarity
  4 Evidence           -> forwards (near-identical text) count as one observation
  5 State engine       -> Engine.recompute(): pending, supported, stale, contradicted, verified, rejected
  6 Geospatial         -> Engine.zone_status(): recent, or UNVERIFIED (never "safe")
  7 Human verification -> review queue, verify/reject, audit log.
                          This module has no dispatch function by design.
"""
import math
import re
from dataclasses import dataclass, field
from typing import Optional

FRESHNESS_MIN = {"road": 30, "bridge": 30, "rescue": 15, "shelter": 60}
CATEGORY_WEIGHT = {"rescue": 3, "road": 2, "bridge": 2, "shelter": 1}
ATTACH_THRESHOLD = 0.6
REVIEW_THRESHOLD = 0.4
MATCH_KM = 2.0
MATCH_MINUTES = 60
UNVERIFIED_AFTER_MIN = 90
FORWARD_SIMILARITY = 0.85

CONDITION_RULES = [
    ("blocked", r"submerg|blocked|flood|closed|cut off|knee|water"),
    ("trapped", r"trapped|stranded|stuck"),
    ("accessible", r"accessible|clear|passable|open"),
    ("full", r"full|capacity|no space"),
]
SEVERE_PATTERN = r"trapped|stranded|injur|dead|children|elderly|pregnant|rescue"


def tokens(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def jaccard(a, b):
    ta, tb = tokens(a), tokens(b)
    union = ta | tb
    return len(ta & tb) / len(union) if union else 0.0


def km_between(a, b):
    r = 6371.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp = p2 - p1
    dl = math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def extract(text, category):
    """Rule-based extraction. Replace with NLP models in the next stage."""
    t = text.lower()
    condition = "unknown"
    for name, pattern in CONDITION_RULES:
        if re.search(pattern, t):
            condition = name
            break
    if re.search(SEVERE_PATTERN, t) or category == "rescue":
        severity = "high"
    elif condition in ("blocked", "trapped"):
        severity = "medium"
    else:
        severity = "low"
    return {"condition": condition, "severity": severity}


@dataclass
class Report:
    id: str
    t: int
    text: str
    category: str
    lat: float
    lon: float
    source: str
    condition: str
    severity: str
    forward_of: Optional[str] = None
    incident_id: Optional[int] = None


@dataclass
class Incident:
    id: int
    category: str
    lat: float
    lon: float
    text: str
    last_t: int
    reports: list = field(default_factory=list)
    status: str = "open"          # open | verified | rejected (human decisions)
    state: str = "pending"
    conflict: Optional[str] = None
    independent: int = 0
    forwards: int = 0
    age: int = 0
    credibility: float = 0.0
    priority: int = 0
    reasons: list = field(default_factory=list)


class Engine:
    def __init__(self, zones=None):
        self.zones = [dict(z, last_t=None) for z in (zones or [])]
        self.now = 0
        self.reports = []
        self.incidents = []
        self.queue = []
        self.audit = []
        self._rid = 0
        self._iid = 0
        self._qid = 0

    # ---- helpers -------------------------------------------------------
    def advance(self, minutes=5):
        self.now += minutes

    def _log(self, actor, action, detail):
        self.audit.append({"t": self.now, "actor": actor, "action": action, "detail": detail})

    def _incident(self, incident_id):
        for inc in self.incidents:
            if inc.id == incident_id:
                return inc
        raise KeyError(f"no incident {incident_id}")

    def _new_incident(self, category, lat, lon, text):
        self._iid += 1
        inc = Incident(self._iid, category, lat, lon, text, self.now)
        self.incidents.append(inc)
        return inc

    def _attach(self, inc, r, action, score):
        r.incident_id = inc.id
        inc.reports.append(r)
        inc.last_t = self.now
        inc.text = r.text
        self._log("system", action, f"{r.id} -> INC-{inc.id} (score {score:.2f})")
        self.recompute(inc)

    # ---- stage 3: matching --------------------------------------------
    def score_match(self, inc, r):
        d = km_between((inc.lat, inc.lon), (r.lat, r.lon))
        dt = abs(self.now - inc.last_t)
        if d > MATCH_KM or dt > MATCH_MINUTES:
            return 0.0
        return 0.5 * (1 - d / MATCH_KM) + 0.3 * (1 - dt / MATCH_MINUTES) + 0.2 * jaccard(inc.text, r.text)

    # ---- stage 1: ingestion --------------------------------------------
    def ingest(self, text, category, lat, lon, source="citizen"):
        self._rid += 1
        ex = extract(text, category)
        r = Report(f"R{self._rid}", self.now, text, category, lat, lon, source, ex["condition"], ex["severity"])
        self.reports.append(r)

        for z in self.zones:
            if km_between((z["lat"], z["lon"]), (lat, lon)) <= MATCH_KM:
                z["last_t"] = self.now

        dup = next((o for o in self.reports[:-1]
                    if o.category == category and jaccard(o.text, text) >= FORWARD_SIMILARITY), None)
        if dup:
            r.forward_of = dup.id

        best, best_score = None, 0.0
        for inc in self.incidents:
            if inc.category != category or inc.status != "open":
                continue
            s = self.score_match(inc, r)
            if s > best_score:
                best, best_score = inc, s

        if best and best_score >= ATTACH_THRESHOLD:
            self._attach(best, r, "attached", best_score)
            action, incident_id = "attached", best.id
        elif best and best_score >= REVIEW_THRESHOLD:
            self._qid += 1
            self.queue.append({"qid": self._qid, "report_id": r.id, "incident_id": best.id,
                               "score": round(best_score, 2), "text": text})
            self._log("system", "queued", f"{r.id} score {best_score:.2f} for INC-{best.id}, needs human")
            action, incident_id = "queued", best.id
        else:
            inc = self._new_incident(category, lat, lon, text)
            self._attach(inc, r, "opened", 0.0)
            action, incident_id = "opened", inc.id

        return {"report_id": r.id, "action": action, "incident_id": incident_id,
                "forward_of": r.forward_of, "condition": r.condition, "severity": r.severity}

    # ---- stage 4 and 5: evidence and state -----------------------------
    def recompute(self, inc):
        indep = [r for r in inc.reports if r.forward_of is None]
        inc.independent = len(indep)
        inc.forwards = len(inc.reports) - len(indep)
        inc.conflict = None
        if not indep:
            return
        latest = indep[-1]
        inc.age = self.now - latest.t

        known = [r for r in indep if r.condition != "unknown"]
        if len(known) >= 2 and known[-1].condition != known[-2].condition:
            inc.conflict = f"{known[-2].id} says {known[-2].condition}, {known[-1].id} says {known[-1].condition}"

        if inc.status == "verified":
            inc.state = "verified"
        elif inc.status == "rejected":
            inc.state = "rejected"
        elif inc.conflict:
            inc.state = "contradicted"
        elif inc.age > FRESHNESS_MIN[inc.category]:
            inc.state = "stale"
        elif inc.independent >= 2:
            inc.state = "supported"
        else:
            inc.state = "pending"

        inc.credibility = round(min(1.0, inc.independent / 3) * math.exp(-inc.age / 60), 2)

        w = CATEGORY_WEIGHT[inc.category]
        reasons = [f"category {inc.category} weight {w}"]
        if inc.state == "contradicted":
            w += 2
            reasons.append("contradicted claims +2")
        if inc.state == "stale":
            w += 1
            reasons.append("stale state +1")
        if latest.severity == "high":
            w += 1
            reasons.append("high severity report +1")
        if inc.status in ("verified", "rejected"):
            w = 0
            reasons = [f"human decision: {inc.status}"]
        inc.priority = w
        inc.reasons = reasons

    # ---- stage 6: geospatial -------------------------------------------
    def zone_status(self):
        out = []
        for z in self.zones:
            if z["last_t"] is None:
                status = "UNVERIFIED (no report yet, not treated as safe)"
            elif self.now - z["last_t"] > UNVERIFIED_AFTER_MIN:
                status = f"UNVERIFIED (last report {self.now - z['last_t']} min ago)"
            else:
                status = f"recent ({self.now - z['last_t']} min ago)"
            out.append({"name": z["name"], "status": status})
        return out

    # ---- stage 7: human review -----------------------------------------
    def verify(self, incident_id, operator, decision):
        if decision not in ("confirm", "reject"):
            raise ValueError("decision must be confirm or reject")
        inc = self._incident(incident_id)
        inc.status = "verified" if decision == "confirm" else "rejected"
        self._log(operator, decision, f"INC-{inc.id} marked {inc.status} by human")
        self.recompute(inc)

    def resolve_queue(self, qid, operator, attach):
        item = next((q for q in self.queue if q["qid"] == qid), None)
        if item is None:
            raise KeyError(f"no queue item {qid}")
        self.queue = [q for q in self.queue if q["qid"] != qid]
        r = next(r for r in self.reports if r.id == item["report_id"])
        if attach:
            inc = self._incident(item["incident_id"])
            self._log(operator, "human-attached", f"{r.id} -> INC-{inc.id}")
        else:
            self._log(operator, "human-rejected-match", f"{r.id} opens a new incident")
            inc = self._new_incident(r.category, r.lat, r.lon, r.text)
        self._attach(inc, r, "human-decision", item["score"])

    # ---- views ----------------------------------------------------------
    def snapshot(self):
        for inc in self.incidents:
            self.recompute(inc)
        ranked = sorted(self.incidents, key=lambda i: (i.priority, CATEGORY_WEIGHT[i.category]), reverse=True)  # tie-break: life-safety category first
        return {
            "now": self.now,
            "kpis": {
                "open_incidents": sum(1 for i in self.incidents if i.status == "open"),
                "reports": len(self.reports),
                "forwards_collapsed": sum(i.forwards for i in self.incidents),
                "contradicted": sum(1 for i in self.incidents if i.state == "contradicted"),
            },
            "incidents": [
                {"id": i.id, "category": i.category, "state": i.state, "status": i.status,
                 "text": i.text, "last_t": i.last_t, "independent": i.independent,
                 "forwards": i.forwards, "age": i.age, "credibility": i.credibility,
                 "conflict": i.conflict, "priority": i.priority, "reasons": i.reasons,
                 "lat": i.lat, "lon": i.lon}
                for i in ranked
            ],
            "queue": self.queue,
            "zones": self.zone_status(),
            "audit": self.audit[-50:][::-1],
        }
