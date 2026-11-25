"""Local web server for the GroundPulse prototype. Standard library only.

Run: python server.py   then open http://127.0.0.1:8000
"""
import json
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from groundpulse.engine import Engine
from groundpulse.scenario import load_engine

HERE = Path(__file__).parent
SCENARIO = HERE / "data" / "demo_scenario.json"
LOCK = threading.Lock()
ENGINE = Engine(zones=[{"name": "Village 9", "lat": 20.27, "lon": 85.84},
                       {"name": "School 4", "lat": 20.30, "lon": 85.90},
                       {"name": "Ward 12", "lat": 20.35, "lon": 85.95}])


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload, ctype="application/json"):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        global ENGINE
        if self.path in ("/", "/index.html"):
            return self._send(200, (HERE / "web" / "index.html").read_bytes(), "text/html; charset=utf-8")
        if self.path == "/api/state":
            with LOCK:
                return self._send(200, ENGINE.snapshot())
        self._send(404, {"error": "not found"})

    def do_POST(self):
        global ENGINE
        try:
            b = self._body()
            with LOCK:
                if self.path == "/api/report":
                    res = ENGINE.ingest(b["text"], b["category"], float(b["lat"]), float(b["lon"]), b.get("source", "citizen"))
                    return self._send(200, res)
                if self.path == "/api/advance":
                    ENGINE.advance(int(b.get("minutes", 5)))
                    return self._send(200, {"now": ENGINE.now})
                if self.path == "/api/verify":
                    ENGINE.verify(int(b["incident_id"]), b.get("operator", "operator"), b["decision"])
                    return self._send(200, {"ok": True})
                if self.path == "/api/resolve":
                    ENGINE.resolve_queue(int(b["qid"]), b.get("operator", "operator"), bool(b["attach"]))
                    return self._send(200, {"ok": True})
                if self.path == "/api/demo":
                    ENGINE = load_engine(SCENARIO)
                    return self._send(200, {"ok": True})
                if self.path == "/api/reset":
                    ENGINE = Engine(zones=ENGINE.zones)
                    return self._send(200, {"ok": True})
            self._send(404, {"error": "not found"})
        except (KeyError, ValueError, StopIteration) as e:
            self._send(400, {"error": str(e)})

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    print("GroundPulse prototype on http://127.0.0.1:8000  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
