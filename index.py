import json
import math
from statistics import fmean
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

# Load telemetry.json from same folder
DATA_PATH = Path(__file__).parent / "telemetry.json"


def p95(values):
    if not values:
        return 0.0
    values = sorted(values)
    index = math.ceil(0.95 * len(values)) - 1
    return values[index]


@app.options("/")
def preflight():
    return JSONResponse(
        {"ok": True},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
    )


@app.post("/")
async def metrics(request: Request):
    body = await request.json()

    regions = body.get("regions")
    threshold = body.get("threshold_ms")

    if not isinstance(regions, list) or not regions:
        return JSONResponse({"error": "regions required"}, status_code=400)

    if not isinstance(threshold, (int, float)):
        return JSONResponse({"error": "threshold_ms required"}, status_code=400)

    with open(DATA_PATH) as f:
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

    return JSONResponse(
        {"regions": results},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
    )
