// Server-side data access with automatic mock fallback.
//
// Each getter calls the live Gold API (src/lib/api.ts). On error (API
// unreachable / 4xx / 5xx) it falls back to the mocks in src/lib/mock.ts —
// which share the exact contract shapes. An *empty* live response only falls
// back when the getter opts in (Gold not yet populated), so a legitimately
// empty answer (e.g. a filtered query with no match) is never masked.
//
// `import "server-only"` makes the build fail if this module is ever imported
// from a Client Component (it would bundle the mocks + API client into the
// browser). It is meant to be called only from async Server Components
// (see src/app/**/page.tsx).
import "server-only";

import {
  ApiError,
  api,
  type ArrondissementMetrics,
  type CityDetail,
  type CityMetrics,
  type Gare,
  type HousingPriceByType,
  type ListArrondissementsParams,
  type ListCitiesParams,
  type ListGaresParams,
  type ListHousingPricesParams,
} from "./api";
import {
  cities as mockCities,
  nationalDetail as mockNationalDetail,
  nationalHousingByType as mockNationalHousing,
  parisArrondissements as mockArrondissements,
  parisDetail as mockCityDetail,
  parisGares as mockGares,
  parisHousingByType as mockHousingByType,
} from "./mock";

// Re-exported from the client-safe geo module so server code keeps a single
// import site for the scope constant.
export { IDF_DEPARTEMENTS } from "./geo";

type FallbackOpts<T> = {
  /** When provided and true for the value, an empty live result falls back to the mock. */
  onEmpty?: (value: T) => boolean;
};

/**
 * Try the live call. Always falls back to the mock on error; falls back on an
 * empty success only when `onEmpty` is given and returns true.
 */
async function liveOrMock<T>(
  label: string,
  live: () => Promise<T>,
  mock: T,
  opts: FallbackOpts<T> = {},
): Promise<T> {
  try {
    const value = await live();
    if (opts.onEmpty?.(value)) {
      console.info(`[data] ${label}: API returned empty, falling back to mock`);
      return mock;
    }
    return value;
  } catch (err) {
    const reason = err instanceof ApiError ? `HTTP ${err.status}` : String(err);
    const cause = (err as { cause?: { code?: string; message?: string } })?.cause;
    console.warn(
      `[data] ${label}: API unavailable (${reason}${cause ? ` | cause: ${cause.code ?? cause.message}` : ""}), falling back to mock`,
    );
    return mock;
  }
}

/** Detail mock for the requested commune — never another city's data. */
function mockCityDetailFor(codeCommune: string): CityDetail {
  if (codeCommune === mockCityDetail.code_commune) return mockCityDetail;
  const city = mockCities.find((c) => c.code_commune === codeCommune);
  // No rich mock for this commune: surface its headline row with empty history
  // instead of falling back to Paris's numbers.
  return city ? { ...city, metrics_by_year: [], trend: [] } : mockCityDetail;
}

/** Housing-by-type mock for the requested commune (empty when we have none for it). */
function mockHousingFor(codeCommune?: string): HousingPriceByType[] {
  if (!codeCommune || codeCommune === mockHousingByType[0]?.code_commune) {
    return mockHousingByType;
  }
  return [];
}

/**
 * Whether the app is currently serving live API data or the mock fallback.
 * Mirrors the unfiltered `getCities` rule: a failed or empty live call means
 * we'd be showing mocks. Cheap probe (size 1) meant for the data-source badge.
 */
export async function getDataSource(): Promise<"live" | "mock"> {
  try {
    const { items } = await api.listCities({ size: 1 });
    return items.length > 0 ? "live" : "mock";
  } catch {
    return "mock";
  }
}

/** City metrics list (headline per commune). Fetches a wide page for client-side filtering/sorting. */
export function getCities(params: ListCitiesParams = {}): Promise<CityMetrics[]> {
  const isFiltered = Boolean(params.departement || params.q);
  return liveOrMock(
    "getCities",
    async () => (await api.listCities({ size: 200, ...params })).items,
    mockCities,
    // A filtered query returning nothing is a real "no match" — don't mask it.
    // An unfiltered empty result means Gold isn't populated yet -> show mocks.
    isFiltered ? {} : { onEmpty: (items) => items.length === 0 },
  );
}

/** Single city detail (+ per-year history + monthly trend). */
export function getCityDetail(codeCommune: string): Promise<CityDetail> {
  return liveOrMock(
    "getCityDetail",
    () => api.getCity(codeCommune),
    mockCityDetailFor(codeCommune),
    { onEmpty: (d) => d.metrics_by_year.length === 0 && d.trend.length === 0 },
  );
}

/**
 * France-wide aggregate, shaped like a city detail (KPIs + trend + yearly
 * history). Powers the "France entière" toggle on the stats page; falls back to
 * the mock aggregate when the API is unreachable.
 */
export function getNationalDetail(): Promise<CityDetail> {
  return liveOrMock("getNationalDetail", () => api.getNational(), mockNationalDetail, {
    onEmpty: (d) => d.metrics_by_year.length === 0 && d.trend.length === 0,
  });
}

/** France-wide per-type (Maison / Appartement) price aggregate. */
export function getNationalHousing(): Promise<HousingPriceByType[]> {
  return liveOrMock(
    "getNationalHousing",
    async () => (await api.listNationalHousing()).items,
    mockNationalHousing,
    { onEmpty: (items) => items.length === 0 },
  );
}

/** Per-dwelling-type (Maison / Appartement) price metrics for a commune. */
export function getHousingByType(
  params: ListHousingPricesParams = {},
): Promise<HousingPriceByType[]> {
  return liveOrMock(
    "getHousingByType",
    async () => (await api.listHousingPrices(params)).items,
    mockHousingFor(params.code_commune),
    { onEmpty: (items) => items.length === 0 },
  );
}

/**
 * Cities across several departments (the map scope). The API filters by a
 * single dept, so we fan out one call per department in parallel and merge.
 * Each dept is capped + sorted by transaction volume, surfacing the communes a
 * buyer actually cares about. Resilient to partial failure: a dept that errors
 * is skipped, not fatal — we only fall back to mocks when *every* call fails.
 */
export async function getCitiesByDepartements(
  departements: string[],
): Promise<CityMetrics[]> {
  const results = await Promise.allSettled(
    departements.map((dep) =>
      api.listCities({ departement: dep, sort: "nb_transactions", order: "desc", size: 200 }),
    ),
  );
  const items = results.flatMap((r) =>
    r.status === "fulfilled" ? r.value.items : [],
  );
  if (items.length > 0) return items;

  const reason = results.find((r) => r.status === "rejected") as
    | PromiseRejectedResult
    | undefined;
  console.warn(
    `[data] getCitiesByDepartements: no live data (${reason ? String(reason.reason) : "empty"}), falling back to mock`,
  );
  return mockCities;
}

/** Arrondissements for a parent commune (Paris/Lyon/Marseille drill-down). */
export function getArrondissements(
  params: ListArrondissementsParams = {},
): Promise<ArrondissementMetrics[]> {
  return liveOrMock(
    "getArrondissements",
    async () => (await api.listArrondissements({ size: 200, ...params })).items,
    mockArrondissements,
    { onEmpty: (items) => items.length === 0 },
  );
}

/** Geolocated train stations for the map's gares layer. */
export function getGares(params: ListGaresParams = {}): Promise<Gare[]> {
  return liveOrMock(
    "getGares",
    async () => (await api.listGares({ size: 1000, ...params })).items,
    mockGares,
    { onEmpty: (items) => items.length === 0 },
  );
}

/** Stations across several departments (gares layer for a multi-dept scope).
 * Resilient to partial failure — a failed dept is skipped, mock only when all
 * calls fail. */
export async function getGaresByDepartements(
  departements: string[],
): Promise<Gare[]> {
  const results = await Promise.allSettled(
    departements.map((dep) => api.listGares({ departement: dep, size: 1000 })),
  );
  const items = results.flatMap((r) =>
    r.status === "fulfilled" ? r.value.items : [],
  );
  return items.length > 0 ? items : mockGares;
}
