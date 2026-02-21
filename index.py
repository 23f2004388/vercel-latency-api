import json
import math
from pathlib import Path
from statistics import fmean
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ✅ Proper CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = Path(__file__).resolve().parent.parent / "telemetry.json"


def p95(values):
    if not values:
        return 0.0
    v = sorted(values)
    k = math.ceil(0.95 * len(v)) - 1
    return v[k]


@app.post("/")
async def metrics(req: Request):
    body = await req.json()
    regions = body.get("regions", [])
    threshold = body.get("threshold_ms")

    if not isinstance(regions, list) or not regions:
        return {"error": "regions required"}

    if not isinstance(threshold, (int, float)):
        return {"error": "threshold_ms required"}

    with DATA_PATH.open() as f:
        data = json.load(f)

    results = []

    for region in regions:
        rows = [r for r in data if r["region"] == region]
        latencies = [r["latency_ms"] for r in rows]
        uptimes = [r["uptime_pct"] for r in rows]

        results.append({
            "region": region,
            "avg_latency": fmean(latencies) if latencies else 0.0,
            "p95_latency": p95(latencies),
            "avg_uptime": fmean(uptimes) if uptimes else 0.0,
            "breaches": sum(1 for x in latencies if x > threshold)
        })

    return {"regions": results}
