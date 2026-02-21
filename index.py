import json
import math
from pathlib import Path
from statistics import fmean

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

DATA_PATH = Path(__file__).parent / "telemetry.json"


def p95(values):
    if not values:
        return 0.0
    values = sorted(values)
    idx = math.ceil(0.95 * len(values)) - 1
    return values[idx]


# ✅ Force CORS headers ALWAYS (even if Origin header is missing)
class ForceCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Handle preflight
        if request.method == "OPTIONS":
            return JSONResponse(
                {"ok": True},
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                },
            )

        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response


app.add_middleware(ForceCORSMiddleware)


@app.post("/")
async def metrics(req: Request):
    body = await req.json()
    regions = body.get("regions", [])
    threshold = body.get("threshold_ms")

    if not isinstance(regions, list) or not regions:
        return JSONResponse({"error": "regions required"}, status_code=400)
    if not isinstance(threshold, (int, float)):
        return JSONResponse({"error": "threshold_ms required"}, status_code=400)

    with DATA_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    out = []
    for region in regions:
        rows = [r for r in data if r.get("region") == region]
        latencies = [r.get("latency_ms", 0) for r in rows]
        uptimes = [r.get("uptime_pct", 0) for r in rows]

        out.append(
            {
                "region": region,
                "avg_latency": fmean(latencies) if latencies else 0.0,
                "p95_latency": p95(latencies),
                "avg_uptime": fmean(uptimes) if uptimes else 0.0,
                "breaches": sum(1 for x in latencies if x > threshold),
            }
        )

    return {"regions": out}
