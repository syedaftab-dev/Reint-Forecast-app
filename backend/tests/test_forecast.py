from datetime import date, time

import pandas as pd

from app.forecast import forecast_vs_actual, select_forecast

DAY = date(2026, 1, 15)
SLOT = "2026-01-15 00:00"


def ts(text: str) -> pd.Timestamp:
    return pd.Timestamp(text, tz="UTC")


def make_forecasts(rows: list[tuple[str, str, int]]) -> pd.DataFrame:
    """rows: (startTime, publishTime, generation)."""
    return pd.DataFrame(
        [(ts(s), ts(p), g) for s, p, g in rows],
        columns=["startTime", "publishTime", "generation"],
    )


def test_forecast_after_cutoff_is_excluded():
    f = make_forecasts([(SLOT, "2026-01-14 07:30", 100), (SLOT, "2026-01-14 09:30", 999)])
    assert select_forecast(f, DAY)["forecast_mw"].tolist() == [100]


def test_latest_version_before_cutoff_is_picked():
    f = make_forecasts([
        (SLOT, "2026-01-14 02:30", 10),
        (SLOT, "2026-01-14 04:30", 20),
        (SLOT, "2026-01-14 07:30", 30),
    ])
    assert select_forecast(f, DAY)["forecast_mw"].tolist() == [30]


def test_publish_exactly_at_cutoff_is_included():
    f = make_forecasts([(SLOT, "2026-01-14 09:00", 50)])
    assert len(select_forecast(f, DAY)) == 1


def test_later_cutoff_picks_newer_version():
    f = make_forecasts([(SLOT, "2026-01-14 07:30", 100), (SLOT, "2026-01-14 09:30", 200)])
    assert select_forecast(f, DAY, time(9, 0))["forecast_mw"].tolist() == [100]
    assert select_forecast(f, DAY, time(10, 0))["forecast_mw"].tolist() == [200]


def test_horizon_hours():
    f = make_forecasts([(SLOT, "2026-01-14 07:30", 100)])
    assert select_forecast(f, DAY)["horizon_h"].tolist() == [16.5]


def test_slot_without_usable_forecast_is_absent():
    f = make_forecasts([(SLOT, "2026-01-14 09:30", 999)])
    assert select_forecast(f, DAY).empty


def test_error_is_forecast_minus_hourly_average_actual():
    f = make_forecasts([(SLOT, "2026-01-14 07:30", 120)])
    a = pd.DataFrame({
        "startTime": [ts("2026-01-15 00:00"), ts("2026-01-15 00:30")],
        "generation": [90, 110],
    })
    result = forecast_vs_actual(f, a, DAY)
    assert result["actual_mw"].tolist() == [100]
    assert result["error_mw"].tolist() == [20]