/** Whole number with thousands separators, e.g. 12,345. */
export const fmt = (n: number): string => Math.round(n).toLocaleString("en-GB");

/** Decision times (UTC, on the day before delivery) the buyer can choose from. */
export const CUTOFFS = ["06:00", "09:00", "12:00", "18:00", "23:00"];