"""HTTP API: thin routes over forecast.py and metrics.py."""
import os
from datetime import date, time
from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.forecast import (
    DEFAULT_CUTOFF,
    DELIVERY_DAYS,
    cutoff_for,
    forecast_vs_actual,
    load_data,
    month_dataset,
)
from app.metrics import add_band, error_by_cutoff, error_by_horizon, error_quantiles, summary

app = FastAPI(title="Wind forecast API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["GET"],
    allow_headers=["*"],
)


@lru_cache
def data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the cached parquet files once."""
    return load_data()


@lru_cache
def month(cutoff: time) -> pd.DataFrame:
    """January forecast-vs-actual table for one cutoff time (cached)."""
    actuals, forecasts = data()
    return month_dataset(forecasts, actuals, cutoff)


@lru_cache
def cutoff_table() -> pd.DataFrame:
    """Accuracy for several decision times (cached, it is the slowest query)."""
    actuals, forecasts = data()
    return error_by_cutoff(forecasts, actuals)


def records(df: pd.DataFrame) -> list[dict]:
    """DataFrame to JSON-safe rows: times become ISO text, NaN becomes null."""
    out = df.copy()
    for column in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[column]):
            out[column] = out[column].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return out.astype(object).where(out.notna(), None).to_dict(orient="records")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}


@app.get("/forecast")
def get_forecast(
    delivery_date: date = Query(..., alias="date"), cutoff: time = DEFAULT_CUTOFF
) -> dict:
    """Latest forecast usable at the cutoff on D-1, with actuals and an error band."""
    if delivery_date not in set(DELIVERY_DAYS):
        raise HTTPException(status_code=400, detail="date must be in January 2026")
    actuals, forecasts = data()
    day = forecast_vs_actual(forecasts, actuals, delivery_date, cutoff)
    if day.empty:
        raise HTTPException(status_code=404, detail="No forecast was available at that cutoff")

    quantiles = error_quantiles(month(cutoff))
    day = add_band(day, quantiles)
    return {
        "delivery_date": delivery_date,
        "cutoff": cutoff_for(delivery_date, cutoff).isoformat(),
        "publish_times": sorted(day["publishTime"].dt.strftime("%Y-%m-%dT%H:%M:%SZ").unique()),
        "quantiles": quantiles,
        "band_is_in_sample": True,
        "summary": {
            "total_forecast_mwh": float(day["forecast_mw"].sum()),
            "total_actual_mwh": float(day["actual_mw"].sum()),
            "min_forecast_mw": float(day["forecast_mw"].min()),
            "peak_forecast_mw": float(day["forecast_mw"].max()),
        },
        "rows": records(day),
    }


@app.get("/accuracy")
def get_accuracy(cutoff: time = DEFAULT_CUTOFF) -> dict:
    """Month-wide forecast accuracy for one decision time."""
    df = month(cutoff)
    return {
        "cutoff": cutoff.strftime("%H:%M"),
        "summary": summary(df),
        "quantiles": error_quantiles(df),
        "by_horizon": records(error_by_horizon(df)),
        "by_cutoff": records(cutoff_table()),
        "points": records(df[["forecast_mw", "actual_mw", "horizon_h"]]),
    }