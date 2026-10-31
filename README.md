# Wind Forecast Desk

A web tool for a UK power buyer who commits day-ahead electricity purchases. It answers two questions:

1. **What is the latest wind forecast I could actually use when I had to decide?**
2. **How accurate have those forecasts been, so I know how much backup power to buy?**

Scope: national wind generation, delivery days 1 to 31 January 2026. Data is from the Elexon BMRS API (FUELHH actuals, WINDFOR forecasts).

## Live demo

- App: https://reint-forecast-app.vercel.app/
- API: https://reint-backend.onrender.com (try `/health` and `/accuracy`)

The API runs on a free tier and sleeps when idle. The first request can take about 50 seconds.

## How it works

The buyer commits power for delivery day D by a cutoff on D-1. For every hour of D, the app picks the forecast with the latest `publishTime` at or before that cutoff. Forecasts published later are never used, because the buyer could not have seen them.

Choices and assumptions:

- **Cutoff:** 09:00 UTC on D-1 by default, selectable in the UI. GB day-ahead auctions close in the morning, so 09:00 is a simple stand-in for gate closure.
- **Time zone:** all times are UTC. In January UK local time equals UTC.
- **Resolution:** WINDFOR forecasts are hourly and FUELHH actuals are half-hourly. Each hour's two actual values are averaged, and everything is compared hourly.
- **Error:** forecast minus actual. Positive means the forecast was too high.
- **Uncertainty band:** the 10th and 90th percentile of forecast error over all of January. This is in-sample, so it describes January and is not a forward-looking guarantee.
- **Horizon:** the hours between publication and the delivery hour. With a fixed cutoff it is tied to the hour of the day.

## Findings (January 2026, 09:00 cutoff)

- Average error (MAE): about 2,142 MW, 18.5% of average wind.
- Bias: about +1,852 MW. Forecasts ran roughly 16% above actual generation, and they track the shape well (correlation 0.93). The error is mostly a level shift, not noise.
- The risk is lopsided: wind came in below the forecast far more often than above it.
- Deciding later helps: using a 23:00 cutoff instead of 09:00 cut average error by about 10%, but the bias stays.
- Possible causes of the over-forecast (curtailment, differences in how the two datasets define generation) are hypotheses, not verified.

## Run it

With Docker:

```
docker compose up --build
```

- App: http://localhost:3000
- API: http://localhost:8000/docs

Without Docker:

```
# backend
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000

# frontend (second terminal)
cd frontend
npm install
npm run dev
```

Tests:

```
cd backend
python -m pytest -v
```

Refresh the cached data from Elexon (not needed to run the app):

```
cd backend
python -m app.ingest
```

## Project layout

```
backend/
  app/
    main.py       HTTP routes (thin)
    forecast.py   picks the forecast usable at the cutoff, joins actuals
    metrics.py    MAE, RMSE, bias, percentiles, error by horizon and cutoff
    ingest.py     downloads Elexon data to Parquet
  data/           cached actuals and forecasts (Parquet)
  tests/          pytest tests for selection logic, metrics and API
frontend/
  src/
    pages/        ForecastPage, AccuracyPage
    components/   KpiCard
    api.ts        calls to the backend
docker-compose.yml
```

Design choice: the January data is small (about 120 KB), so it is committed as Parquet and loaded once at start. There is no database, and the deployed app does not depend on the Elexon API being up.

## Tests

The tests cover the business rules: no hindsight forecasts, latest version before the cutoff wins, a forecast published exactly at the cutoff is allowed, a later cutoff picks a newer version, horizon and error sign, and the metrics.

## AI tools used

Antigravity (AI coding agent) and Claude were used for planning, code generation and review. I verified the data, the selection logic and the tests myself.

## Limitations and next steps

- Only January 2026 and national-level wind.
- The error band is in-sample. A rolling out-of-sample band would be more honest for live use.
- Bias could be corrected by a simple calibration, once its cause is understood.
- Extending the range needs a re-run of `ingest.py` and a change to the delivery-day range in `forecast.py`.