"""Pick the wind forecast a buyer could actually use, and compare it to actuals."""
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_CUTOFF = time(9, 0)
DELIVERY_DAYS = pd.date_range("2026-01-01", "2026-01-31").date


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read cached actuals and forecasts (written by ingest.py)."""
    actuals = pd.read_parquet(DATA_DIR / "actuals.parquet")
    forecasts = pd.read_parquet(DATA_DIR / "forecasts.parquet")
    return actuals, forecasts


def cutoff_for(delivery_date: date, cutoff_time: time = DEFAULT_CUTOFF) -> pd.Timestamp:
    """Decision deadline: cutoff_time (UTC) on the day before delivery."""
    day_before = delivery_date - timedelta(days=1)
    return pd.Timestamp(datetime.combine(day_before, cutoff_time)).tz_localize("UTC")


def hourly_actuals(actuals: pd.DataFrame) -> pd.DataFrame:
    """Forecasts are hourly, actuals are half-hourly: average each hour's two values."""
    hour = actuals["startTime"].dt.floor("h")
    averaged = actuals.groupby(hour)["generation"].mean()
    return averaged.rename("actual_mw").reset_index()


def select_forecast(
    forecasts: pd.DataFrame, delivery_date: date, cutoff_time: time = DEFAULT_CUTOFF
) -> pd.DataFrame:
    """For each hour of delivery_date, keep the latest forecast published
    at or before the cutoff. Later forecasts are never used (no hindsight)."""
    cutoff = cutoff_for(delivery_date, cutoff_time)
    day_start = pd.Timestamp(delivery_date).tz_localize("UTC")
    day_end = day_start + pd.Timedelta(days=1)

    in_day = (forecasts["startTime"] >= day_start) & (forecasts["startTime"] < day_end)
    usable = forecasts[in_day & (forecasts["publishTime"] <= cutoff)].reset_index(drop=True)

    latest = usable.loc[usable.groupby("startTime")["publishTime"].idxmax()]
    result = latest.rename(columns={"generation": "forecast_mw"})
    result = result[["startTime", "publishTime", "forecast_mw"]].copy()
    result["horizon_h"] = (result["startTime"] - result["publishTime"]).dt.total_seconds() / 3600
    return result.sort_values("startTime").reset_index(drop=True)


def forecast_vs_actual(
    forecasts: pd.DataFrame,
    actuals: pd.DataFrame,
    delivery_date: date,
    cutoff_time: time = DEFAULT_CUTOFF,
) -> pd.DataFrame:
    """Selected forecast joined with hourly actuals. error = forecast - actual."""
    selected = select_forecast(forecasts, delivery_date, cutoff_time)
    merged = selected.merge(hourly_actuals(actuals), on="startTime", how="left")
    merged["error_mw"] = merged["forecast_mw"] - merged["actual_mw"]
    return merged


def month_dataset(
    forecasts: pd.DataFrame, actuals: pd.DataFrame, cutoff_time: time = DEFAULT_CUTOFF
) -> pd.DataFrame:
    """forecast_vs_actual for every delivery day in January 2026."""
    frames = [
        forecast_vs_actual(forecasts, actuals, day, cutoff_time).assign(delivery_date=day)
        for day in DELIVERY_DAYS
    ]
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    """Print sanity checks on the real data."""
    actuals, forecasts = load_data()
    for day in [date(2026, 1, 1), date(2026, 1, 15), date(2026, 1, 31)]:
        df = forecast_vs_actual(forecasts, actuals, day)
        print(day, "rows:", len(df),
              "publishTimes:", sorted(df["publishTime"].dt.strftime("%Y-%m-%dT%H:%M").unique()),
              "horizon min/max:", df["horizon_h"].min(), df["horizon_h"].max(),
              "null actuals:", int(df["actual_mw"].isna().sum()))
    month = month_dataset(forecasts, actuals)
    print("month rows:", len(month), "(expect 744)")
    print("month null actuals:", int(month["actual_mw"].isna().sum()))


if __name__ == "__main__":
    main()