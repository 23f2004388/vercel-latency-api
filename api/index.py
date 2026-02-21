import json
import math
from pathlib import Path
from statistics import fmean
from typing import List, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS for POST from any origin (and OPTIONS preflight)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

DATA_PATH = Path(__file__).resolve().parent.parent / "telemetry.json"

def p95(values: List[float]) -> float:
    if not values:
        return 0.0
    v = sorted(values)
    k = math.ceil(0.95 * len(v)) - 1
    return float(v[k])

@app.post("/api")
async def metrics(payload: dict):
    regions = payload.get("regions", [])
    threshold = payload.get("threshold_ms")

    if not isinstance(regions, list) or not regions:
        return {"error": "regions required"}
    if not isinstance(threshold, (int, float)):
        return {"error": "threshold_ms required"}

    with DATA_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    results = []
    for region in regions:
        rows = [r for r in data if r.get("region") == region]
        latencies = [float(r.get("latency_ms", 0.0)) for r in rows]
        uptimes = [float(r.get("uptime_pct", 0.0)) for r in rows]

        results.append(
            {
                "region": region,
                "avg_latency": float(fmean(latencies)) if latencies else 0.0,
                "p95_latency": p95(latencies),
                "avg_uptime": float(fmean(uptimes)) if uptimes else 0.0,
                "breaches": int(sum(1 for x in latencies if x > threshold)),
            }
        )

    return {"regions": results}
