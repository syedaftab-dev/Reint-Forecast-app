import type { AccuracyResponse, ForecastResponse } from "./types";

const BASE: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

export const fetchForecast = (date: string, cutoff: string) =>
  get<ForecastResponse>(`/forecast?date=${date}&cutoff=${cutoff}`);

export const fetchAccuracy = (cutoff: string) =>
  get<AccuracyResponse>(`/accuracy?cutoff=${cutoff}`);