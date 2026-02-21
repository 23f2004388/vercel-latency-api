from http.server import BaseHTTPRequestHandler
import json
import os
from statistics import mean

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}

ROOT = os.path.dirname(os.path.dirname(__file__))  # repo root
DATA_PATH = os.path.join(ROOT, "telemetry.json")

with open(DATA_PATH, "r", encoding="utf-8") as f:
    TELEMETRY = json.load(f)

def p95(values):
    if not values:
        return 0
    s = sorted(values)
    idx = int(0.95 * (len(s) - 1))
    return s[idx]

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("content-length", 0))
            raw = self.rfile.read(length).decode("utf-8")
            req = json.loads(raw) if raw else {}

            regions = req.get("regions", [])
            threshold_ms = req.get("threshold_ms", 180)

            out = {}
            for r in regions:
                rows = [x for x in TELEMETRY if x.get("region") == r]
                lat = [x.get("latency_ms", 0) for x in rows]
                upt = [x.get("uptime", x.get("uptime_ratio", 0)) for x in rows]

                out[r] = {
                    "avg_latency": mean(lat) if lat else 0,
                    "p95_latency": p95(lat),
                    "avg_uptime": mean(upt) if upt else 0,
                    "breaches": sum(1 for v in lat if v > threshold_ms),
                }

            self.send_response(200)
            for k, v in CORS_HEADERS.items():
                self.send_header(k, v)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(out).encode("utf-8"))

        except Exception as e:
            self.send_response(500)
            for k, v in CORS_HEADERS.items():
                self.send_header(k, v)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
