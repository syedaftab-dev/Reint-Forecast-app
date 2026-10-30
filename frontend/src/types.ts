export interface ForecastRow {
  startTime: string;
  publishTime: string;
  forecast_mw: number;
  horizon_h: number;
  actual_mw: number | null;
  error_mw: number | null;
  low_mw: number;
  high_mw: number;
}

export interface ForecastResponse {
  delivery_date: string;
  cutoff: string;
  publish_times: string[];
  quantiles: { p10: number; p90: number };
  band_is_in_sample: boolean;
  summary: {
    total_forecast_mwh: number;
    total_actual_mwh: number;
    min_forecast_mw: number;
    peak_forecast_mw: number;
  };
  rows: ForecastRow[];
}

export interface HorizonRow {
  horizon_h: number;
  mae_mw: number;
  bias_mw: number;
  n: number;
}

export interface CutoffRow {
  cutoff: string;
  n: number;
  mae_mw: number;
  rmse_mw: number;
  bias_mw: number;
}

export interface AccuracyResponse {
  cutoff: string;
  summary: {
    n: number;
    mae_mw: number;
    rmse_mw: number;
    bias_mw: number;
    p90_abs_error_mw: number;
    mean_actual_mw: number;
    mae_pct_of_mean: number;
  };
  quantiles: { p10: number; p90: number };
  by_horizon: HorizonRow[];
  by_cutoff: CutoffRow[];
  points: { forecast_mw: number; actual_mw: number; horizon_h: number }[];
}