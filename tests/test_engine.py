import unittest
from pathlib import Path

from groundpulse.engine import Engine, jaccard
from groundpulse.scenario import load_engine

SCENARIO = Path(__file__).resolve().parent.parent / "data" / "demo_scenario.json"
ROAD = (20.27, 85.84)


class DemoScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.eng = load_engine(SCENARIO)
        cls.snap = cls.eng.snapshot()

    def road(self):
        return next(i for i in self.snap["incidents"] if i["category"] == "road")

    def test_six_forwards_collapse_to_one_observation(self):
        road = self.road()
        self.assertEqual(road["forwards"], 6)
        # independent = citizen report + field responder report
        self.assertEqual(road["independent"], 2)

    def test_later_report_flips_road_to_contradicted(self):
        road = self.road()
        self.assertEqual(road["state"], "contradicted")
        self.assertIn("accessible", road["conflict"])
        self.assertIn("blocked", road["conflict"])

    def test_zone_with_no_report_is_unverified_not_safe(self):
        zones = {z["name"]: z["status"] for z in self.snap["zones"]}
        self.assertTrue(zones["Ward 12"].startswith("UNVERIFIED"))
        self.assertTrue(zones["Village 9"].startswith("recent"))

    def test_rescue_is_high_severity_and_ranked_first(self):
        top = self.snap["incidents"][0]
        self.assertEqual(top["category"], "rescue")

    def test_no_dispatch_capability(self):
        self.assertFalse(hasattr(Engine, "dispatch"))
        actions = {a["action"] for a in self.snap["audit"]}
        self.assertNotIn("dispatch", actions)


class RuleTests(unittest.TestCase):
    def test_stale_after_freshness_window(self):
        eng = Engine()
        eng.ingest("Road to Village 9 is accessible", "road", *ROAD)
        eng.ingest("Road to Village 9 is accessible, vehicles pass", "road", *ROAD)
        eng.advance(40)  # road freshness is 30 min
        snap = eng.snapshot()
        self.assertEqual(snap["incidents"][0]["state"], "stale")

    def test_borderline_match_goes_to_human_queue(self):
        eng = Engine()
        eng.ingest("Road to Village 9 is accessible", "road", *ROAD)
        eng.advance(50)
        res = eng.ingest("Road blocked by debris", "road", *ROAD)
        self.assertEqual(res["action"], "queued")
        self.assertEqual(len(eng.queue), 1)

    def test_human_reject_opens_new_incident(self):
        eng = Engine()
        eng.ingest("Road to Village 9 is accessible", "road", *ROAD)
        eng.advance(50)
        eng.ingest("Road blocked by debris", "road", *ROAD)
        qid = eng.queue[0]["qid"]
        eng.resolve_queue(qid, "tester", attach=False)
        self.assertEqual(len(eng.incidents), 2)
        self.assertEqual(eng.queue, [])

    def test_confirm_sets_verified_and_zeroes_priority(self):
        eng = Engine()
        eng.ingest("Road to Village 9 is accessible", "road", *ROAD)
        eng.verify(1, "tester", "confirm")
        inc = eng.snapshot()["incidents"][0]
        self.assertEqual(inc["state"], "verified")
        self.assertEqual(inc["priority"], 0)

    def test_forwards_do_not_count_as_independent(self):
        eng = Engine()
        for _ in range(4):
            eng.ingest("Bridge damaged at Village 9", "bridge", *ROAD, source="forwarded message")
        inc = eng.snapshot()["incidents"][0]
        self.assertEqual(inc["independent"], 1)

    def test_jaccard_identical_is_one(self):
        self.assertEqual(jaccard("a b c", "a b c"), 1.0)


if __name__ == "__main__":
    unittest.main()
