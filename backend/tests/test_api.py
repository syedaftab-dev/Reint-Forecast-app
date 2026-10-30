import pandas as pd
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_forecast_has_24_hours_and_no_hindsight():
    body = client.get("/forecast", params={"date": "2026-01-15", "cutoff": "09:00"}).json()
    cutoff = pd.Timestamp(body["cutoff"])
    assert len(body["rows"]) == 24
    assert all(pd.Timestamp(row["publishTime"]) <= cutoff for row in body["rows"])


def test_date_outside_january_is_rejected():
    assert client.get("/forecast", params={"date": "2026-02-01"}).status_code == 400


def test_accuracy_has_all_sections():
    body = client.get("/accuracy").json()
    assert set(body) >= {"summary", "quantiles", "by_horizon", "by_cutoff", "points"}
    assert len(body["points"]) == 744
    