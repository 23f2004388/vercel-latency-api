import json
import math
from pathlib import Path
from statistics import fmean
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

# CORS headers we will always return
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
    "Access-Control-Allow-Headers": "*",
}

# telemetry.json is in repo root
DATA_PATH = Path(__file__).parent / "telemetry.json"


def p95(values):
    if not values:
        return 0.0
    values = sorted(values)
    idx = math.ceil(0.95 * len(values)) - 1
    return float(values[idx])


@app.options("/api")
def preflight():
    return JSONResponse({"ok": True}, headers=CORS_HEADERS)


@app.post("/api")
async def metrics(req: Request):
    try:
        body = await req.json()
        regions = body.get("regions")
        threshold = body.get("threshold_ms")

        if not isinstance(regions, list) or not regions:
            return JSONResponse({"error": "regions required"}, status_code=400, headers=CORS_HEADERS)

        if not isinstance(threshold, (int, float)):
            return JSONResponse({"error": "threshold_ms required"}, status_code=400, headers=CORS_HEADERS)

        with DATA_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)

        results = []

        for region in regions:
            rows = [r for r in data if r.get("region") == region]
            latencies = [float(r.get("latency_ms", 0)) for r in rows]
            uptimes = [float(r.get("uptime_pct", 0)) for r in rows]

            results.append({
                "region": region,
                "avg_latency": float(fmean(latencies)) if latencies else 0.0,
                "p95_latency": p95(latencies),
                "avg_uptime": float(fmean(uptimes)) if uptimes else 0.0,
                "breaches": int(sum(1 for x in latencies if x > threshold))
            })

        return JSONResponse({"regions": results}, headers=CORS_HEADERS)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500, headers=CORS_HEADERS)
