from datetime import time

import pandas as pd

from app.metrics import add_band, error_by_cutoff, error_by_horizon, error_quantiles, summary


def ts(text: str) -> pd.Timestamp:
    return pd.Timestamp(text, tz="UTC")


def make_df(forecast: list[float], actual: list[float], horizon: list[float]) -> pd.DataFrame:
    df = pd.DataFrame({"forecast_mw": forecast, "actual_mw": actual, "horizon_h": horizon})
    df["error_mw"] = df["forecast_mw"] - df["actual_mw"]
    return df


def test_summary_mae_rmse_bias():
    result = summary(make_df([103, 97], [100, 100], [1, 2]))
    assert result["mae_mw"] == 3
    assert result["rmse_mw"] == 3
    assert result["bias_mw"] == 0


def test_bias_is_positive_when_forecast_too_high():
    assert summary(make_df([110, 120], [100, 100], [1, 2]))["bias_mw"] == 15


def test_summary_ignores_rows_without_actual():
    df = make_df([110, 50], [100, float("nan")], [1, 2])
    assert summary(df)["n"] == 1


def test_error_by_horizon_groups_rows():
    df = make_df([110, 90, 130], [100, 100, 100], [16.5, 16.5, 17.5])
    result = error_by_horizon(df).set_index("horizon_h")
    assert result.loc[16.5, "mae_mw"] == 10
    assert result.loc[16.5, "bias_mw"] == 0
    assert result.loc[17.5, "mae_mw"] == 30


def test_band_uses_error_quantiles_and_never_goes_below_zero():
    quantiles = {"p10": -10.0, "p90": 20.0}
    banded = add_band(make_df([100, 5], [90, 5], [1, 2]), quantiles)
    assert banded["low_mw"].tolist() == [80, 0]
    assert banded["high_mw"].tolist() == [110, 15]


def test_error_quantiles():
    result = error_quantiles(make_df(list(range(1, 12)), [0] * 11, [1] * 11))
    assert result["p10"] == 2
    assert result["p90"] == 10


def test_later_cutoff_gives_lower_error_when_newer_forecast_is_better():
    forecasts = pd.DataFrame({
        "startTime": [ts("2026-01-15 00:00")] * 2,
        "publishTime": [ts("2026-01-14 07:30"), ts("2026-01-14 09:30")],
        "generation": [100, 200],
    })
    actuals = pd.DataFrame({
        "startTime": [ts("2026-01-15 00:00"), ts("2026-01-15 00:30")],
        "generation": [200, 200],
    })
    result = error_by_cutoff(forecasts, actuals, [time(9, 0), time(10, 0)]).set_index("cutoff")
    assert result.loc["09:00", "mae_mw"] == 100
    assert result.loc["10:00", "mae_mw"] == 0