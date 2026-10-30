"""Download Elexon wind actuals and forecasts and cache them as Parquet files."""
import time
from datetime import date, timedelta
from pathlib import Path

import httpx
import pandas as pd

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

ACTUALS_START, ACTUALS_END = date(2026, 1, 1), date(2026, 1, 31)
FORECAST_START, FORECAST_END = date(2025, 12, 25), date(2026, 1, 31)
EXPECTED_ACTUAL_ROWS = 31 * 48  # 31 days x 48 half-hours


def days_between(start: date, end: date) -> list[date]:
    """Every date from start to end, inclusive."""
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def fetch(client: httpx.Client, dataset: str, params: dict) -> list[dict]:
    """Call one Elexon stream endpoint, retrying a few times. Returns JSON rows."""
    url = f"{BASE_URL}/{dataset}/stream"
    for attempt in range(1, 4):
        try:
            response = client.get(url, params=params, headers={"Accept": "application/json"})
            response.raise_for_status()
            if "json" not in response.headers.get("content-type", ""):
                raise ValueError(f"Response is not JSON: {response.text[:200]}")
            rows = response.json()
            if not rows:
                raise ValueError("empty response")
            return rows
        except (httpx.HTTPError, ValueError) as error:
            print(f"  attempt {attempt} failed for {params}: {error}")
            time.sleep(2)
    raise RuntimeError(f"Giving up on {dataset} {params}")


def ingest_actuals(client: httpx.Client) -> pd.DataFrame:
    """Actual wind generation (MW) for every half-hour of January 2026."""
    rows: list[dict] = []
    for day in days_between(ACTUALS_START, ACTUALS_END):
        params = {
            "settlementDateFrom": day.isoformat(),
            "settlementDateTo": day.isoformat(),
            "fuelType": "WIND",
        }
        rows += fetch(client, "FUELHH", params)

    df = pd.DataFrame(rows)[["startTime", "generation"]]
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df = df.drop_duplicates("startTime").sort_values("startTime").reset_index(drop=True)

    expected = pd.date_range("2026-01-01 00:00", "2026-01-31 23:30", freq="30min", tz="UTC")
    missing = expected.difference(df["startTime"])
    unexpected = pd.DatetimeIndex(df["startTime"]).difference(expected)
    print(f"missing slots = {len(missing)}, unexpected slots = {len(unexpected)}")
    assert len(df) == EXPECTED_ACTUAL_ROWS, f"actuals rows {len(df)} != {EXPECTED_ACTUAL_ROWS}"
    return df


def ingest_forecasts(client: httpx.Client) -> pd.DataFrame:
    """Every wind forecast version published between FORECAST_START and FORECAST_END."""
    rows: list[dict] = []
    for day in days_between(FORECAST_START, FORECAST_END):
        params = {
            "publishDateTimeFrom": f"{day.isoformat()}T00:00:00Z",
            "publishDateTimeTo": f"{day.isoformat()}T23:59:59Z",
        }
        day_rows = fetch(client, "WINDFOR", params)
        print(f"{day}: {len(day_rows)} rows")
        rows += day_rows

    df = pd.DataFrame(rows)[["startTime", "publishTime", "generation"]]
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    df = df.drop_duplicates(["startTime", "publishTime"])
    return df.sort_values(["publishTime", "startTime"]).reset_index(drop=True)


def check_publish_coverage(forecasts: pd.DataFrame) -> None:
    """Fail if any publish day has no forecasts; warn if it has fewer than 8 versions."""
    per_day = forecasts.groupby(forecasts["publishTime"].dt.date)["publishTime"].nunique()
    for day in days_between(FORECAST_START, FORECAST_END):
        count = int(per_day.get(day, 0))
        if count == 0:
            raise AssertionError(f"No publishTimes for date {day}")
        if count < 8:
            print(f"warning: {day} has only {count} distinct publishTimes")


def publish_times(forecasts: pd.DataFrame, day: str) -> list[str]:
    """Distinct publishTimes on one date, as text (for the summary)."""
    on_day = forecasts[forecasts["publishTime"].dt.strftime("%Y-%m-%d") == day]
    return sorted(on_day["publishTime"].dt.strftime("%Y-%m-%dT%H:%M:%SZ").unique())


def main() -> None:
    """Download both datasets, check them, save to backend/data/."""
    DATA_DIR.mkdir(exist_ok=True)
    with httpx.Client(timeout=60) as client:
        actuals = ingest_actuals(client)
        forecasts = ingest_forecasts(client)
    check_publish_coverage(forecasts)

    actuals.to_parquet(DATA_DIR / "actuals.parquet", index=False)
    forecasts.to_parquet(DATA_DIR / "forecasts.parquet", index=False)

    print(f"actuals: rows = {len(actuals)}, "
          f"{actuals['startTime'].min()} .. {actuals['startTime'].max()}")
    print(f"forecasts: rows = {len(forecasts)}, "
          f"publishTime {forecasts['publishTime'].min()} .. {forecasts['publishTime'].max()}")
    print("publishTimes 2025-12-31:", publish_times(forecasts, "2025-12-31"))
    print("publishTimes 2026-01-15:", publish_times(forecasts, "2026-01-15"))


if __name__ == "__main__":
    main()