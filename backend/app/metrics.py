"""Forecast accuracy numbers. Error = forecast - actual (MW); positive = over-forecast."""
from datetime import time

import pandas as pd

from app.forecast import load_data, month_dataset

# DEFAULT_CUTOFFS = [time(0, 0), time(6, 0), time(9, 0), time(12, 0), time(18, 0), time(23, 0)]
DEFAULT_CUTOFFS = [time(6, 0), time(9, 0), time(12, 0), time(18, 0), time(23, 0)]


def summary(df: pd.DataFrame) -> dict[str, float]:
    """Headline accuracy numbers over all rows that have an actual."""
    df = df.dropna(subset=["actual_mw"])
    error = df["error_mw"]
    mean_actual = df["actual_mw"].mean()
    mae = error.abs().mean()
    return {
        "n": len(df),
        "mae_mw": float(mae),
        "rmse_mw": float((error**2).mean() ** 0.5),
        "bias_mw": float(error.mean()),
        "p90_abs_error_mw": float(error.abs().quantile(0.9)),
        "mean_actual_mw": float(mean_actual),
        "mae_pct_of_mean": float(mae / mean_actual * 100),
    }


def error_by_horizon(df: pd.DataFrame) -> pd.DataFrame:
    """MAE and bias for each forecast horizon (hours between publish and target)."""
    df = df.dropna(subset=["actual_mw"]).copy()
    df["abs_error_mw"] = df["error_mw"].abs()
    grouped = df.groupby("horizon_h").agg(
        mae_mw=("abs_error_mw", "mean"),
        bias_mw=("error_mw", "mean"),
        n=("error_mw", "size"),
    )
    return grouped.reset_index()


def error_by_cutoff(
    forecasts: pd.DataFrame, actuals: pd.DataFrame, cutoffs: list[time] = DEFAULT_CUTOFFS
) -> pd.DataFrame:
    """Accuracy if the buyer decided at different times on D-1 (later = newer forecast)."""
    rows = []
    for cutoff in cutoffs:
        stats = summary(month_dataset(forecasts, actuals, cutoff))
        rows.append({"cutoff": cutoff.strftime("%H:%M"), **stats})
    return pd.DataFrame(rows)[["cutoff", "n", "mae_mw", "rmse_mw", "bias_mw"]]


def error_quantiles(df: pd.DataFrame) -> dict[str, float]:
    """P10 and P90 of the error. Used to draw an uncertainty band (in-sample)."""
    error = df["error_mw"].dropna()
    return {"p10": float(error.quantile(0.1)), "p90": float(error.quantile(0.9))}


def add_band(df: pd.DataFrame, quantiles: dict[str, float]) -> pd.DataFrame:
    """Add low_mw / high_mw: likely range of actual wind given the forecast.
    actual = forecast - error, so the high error quantile gives the low end."""
    out = df.copy()
    out["low_mw"] = (out["forecast_mw"] - quantiles["p90"]).clip(lower=0)
    out["high_mw"] = out["forecast_mw"] - quantiles["p10"]
    return out


def main() -> None:
    """Print metrics on the real data."""
    actuals, forecasts = load_data()
    month = month_dataset(forecasts, actuals)
    print("SUMMARY (cutoff 09:00)")
    print(summary(month))
    print("\nQUANTILES", error_quantiles(month))
    print("\nBY HORIZON")
    print(error_by_horizon(month).round(1).to_string(index=False))
    print("\nBY CUTOFF")
    print(error_by_cutoff(forecasts, actuals).round(1).to_string(index=False))


if __name__ == "__main__":
    main()