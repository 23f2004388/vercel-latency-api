import json
import math
from pathlib import Path
from statistics import fmean

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
    "Access-Control-Allow-Headers": "*",
}

# Robust path: try same folder, then parent folder
HERE = Path(__file__).resolve().parent
CANDIDATES = [HERE / "telemetry.json", HERE.parent / "telemetry.json"]


def load_data():
    for p in CANDIDATES:
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError("telemetry.json not found next to index.py or parent folder")


def p95(values):
    if not values:
        return 0.0
    v = sorted(values)
    idx = math.ceil(0.95 * len(v)) - 1
    return float(v[idx])


@app.options("/")
def preflight():
    return JSONResponse({"ok": True}, headers=CORS_HEADERS)


@app.post("/")
async def metrics(req: Request):
    try:
        body = await req.json()
        regions = body.get("regions", [])
        threshold = body.get("threshold_ms", None)

        if not isinstance(regions, list) or len(regions) == 0:
            return JSONResponse({"error": "regions required"}, status_code=400, headers=CORS_HEADERS)
        if not isinstance(threshold, (int, float)):
            return JSONResponse({"error": "threshold_ms required"}, status_code=400, headers=CORS_HEADERS)

        data = load_data()

        results = []
        for region in regions:
            rows = [r for r in data if r.get("region") == region]
            lat = [float(r.get("latency_ms", 0)) for r in rows]
            upt = [float(r.get("uptime_pct", 0)) for r in rows]

            results.append({
                "region": region,
                "avg_latency": float(fmean(lat)) if lat else 0.0,
                "p95_latency": p95(lat),
                "avg_uptime": float(fmean(upt)) if upt else 0.0,
                "breaches": int(sum(1 for x in lat if x > threshold)),
            })

        return JSONResponse({"regions": results}, headers=CORS_HEADERS)

    except Exception as e:
        # so you don't get silent 500s
        return JSONResponse({"error": str(e)}, status_code=500, headers=CORS_HEADERS)
