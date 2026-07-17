// Lightweight median-price projection for the yearly chart.
//
// Fits a least-squares linear trend to the historical yearly median prices and
// extrapolates the next few years. It's a deliberately simple, explainable
// estimate (not an ML model) — enough to sketch where prices are heading.

export type YearPrice = { year: number; prix: number };

/**
 * Project `horizon` future years from a linear trend over `history`.
 * Returns [] when there aren't enough points (< 3) or the trend is flat/degenerate.
 */
export function forecastPrices(history: YearPrice[], horizon = 3): YearPrice[] {
  const pts = history
    .filter((p) => Number.isFinite(p.prix))
    .sort((a, b) => a.year - b.year);
  if (pts.length < 3) return [];

  const n = pts.length;
  const meanX = pts.reduce((s, p) => s + p.year, 0) / n;
  const meanY = pts.reduce((s, p) => s + p.prix, 0) / n;

  let num = 0;
  let den = 0;
  for (const p of pts) {
    num += (p.year - meanX) * (p.prix - meanY);
    den += (p.year - meanX) ** 2;
  }
  if (den === 0) return [];

  const slope = num / den;
  const intercept = meanY - slope * meanX;
  const lastYear = pts[n - 1].year;

  return Array.from({ length: horizon }, (_, i) => {
    const year = lastYear + i + 1;
    return { year, prix: Math.max(0, Math.round(slope * year + intercept)) };
  });
}
