// Typed HTTP client for the HOMEPEDIA Gold API.
//
// Types come from src/lib/api-types.ts (generated from /openapi.json via
// `npx openapi-typescript`). Regenerate after backend changes:
//   npx openapi-typescript http://localhost:8001/openapi.json -o src/lib/api-types.ts
//
// Wired into the UI via src/lib/data.ts (live calls + mock fallback). The Gold
// API serves the enriched commune/arrondissement/gares datasets; mocks in
// src/lib/mock.ts share these exact shapes for offline fallback.
//
// Base URL: NEXT_PUBLIC_API_URL (default http://localhost:8001 — the dev API is
// published on host port 8001). Note: this is inlined at BUILD time. In dev
// setups where Node resolves `localhost` to IPv6 first, set it to
// http://127.0.0.1:8001 (e.g. frontend/.env.local) to avoid ECONNREFUSED on the
// server-side fetch.

import type { components } from "./api-types";

export type CityMetrics = components["schemas"]["CityMetrics"];
export type CityDetail = components["schemas"]["CityDetail"];
export type PriceTrendPoint = components["schemas"]["PriceTrendPoint"];
export type HousingPriceByType = components["schemas"]["HousingPriceByType"];
export type ArrondissementMetrics =
  components["schemas"]["ArrondissementMetrics"];
export type ArrondissementDetail =
  components["schemas"]["ArrondissementDetail"];
export type Gare = components["schemas"]["Gare"];

export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
};

// Server-side (Node/SSR) calls the API over the internal Docker network via
// API_INTERNAL_URL (prod: http://api:8000) to dodge a public round-trip / NAT
// hairpin; the browser uses the public NEXT_PUBLIC_API_URL. `||` (not `??`) so
// an empty-string env value falls back instead of yielding a relative URL.
const BASE_URL = (
  (typeof window === "undefined" ? process.env.API_INTERNAL_URL : "") ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8001"
).replace(/\/+$/, "");

/** Thrown on any non-2xx response, carrying the status and parsed `detail`. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly url: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type QueryValue = string | number | boolean | null | undefined;

async function get<T>(
  path: string,
  params: Record<string, QueryValue> = {},
  init?: RequestInit,
): Promise<T> {
  const url = new URL(`${BASE_URL}${path}`);
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }

  const res = await fetch(url, {
    // Default to fresh data; override per call (e.g. { next: { revalidate: 300 } }).
    cache: "no-store",
    ...init,
    headers: { Accept: "application/json", ...init?.headers },
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // non-JSON error body — keep the status text
    }
    throw new ApiError(res.status, url.toString(), `API ${res.status}: ${detail}`);
  }

  return (await res.json()) as T;
}

// --- Endpoints --------------------------------------------------------------

export type ListCitiesParams = {
  /** Filter by 2-3 char department code (e.g. "75"). */
  departement?: string;
  /** Case-insensitive commune name search. */
  q?: string;
  /** Sort column (default "prix_m2_median"). */
  sort?: string;
  order?: "asc" | "desc";
  page?: number;
  /** 1-200 (default 50). */
  size?: number;
};

export type ListHousingPricesParams = {
  code_commune?: string;
  /** "Maison" | "Appartement". */
  type_local?: string;
  page?: number;
  size?: number;
};

export type ListArrondissementsParams = {
  /** Department code: "75" (Paris) | "69" (Lyon) | "13" (Marseille). */
  departement?: string;
  /** Parent commune INSEE code (e.g. "75056" for Paris). */
  code_commune_parent?: string;
  sort?: string;
  order?: "asc" | "desc";
  page?: number;
  size?: number;
};

export type ListGaresParams = {
  /** 2-char department code. */
  departement?: string;
  code_commune?: string;
  page?: number;
  /** 1-2000 (default 200). */
  size?: number;
};

export const api = {
  /** Readiness probe — connectivity to postgres / redis / s3. */
  ready: (init?: RequestInit) =>
    get<{ status: string; components: Record<string, { ok: boolean; detail: string }> }>(
      "/ready",
      {},
      init,
    ),

  /** Paginated city metrics (Gold gold.city_metrics). */
  listCities: (params: ListCitiesParams = {}, init?: RequestInit) =>
    get<Page<CityMetrics>>("/api/v1/cities", params, init),

  /** Single city detail + monthly price trend. */
  getCity: (codeCommune: string, init?: RequestInit) =>
    get<CityDetail>(`/api/v1/cities/${encodeURIComponent(codeCommune)}`, {}, init),

  /** France-wide aggregate, shaped like a city (KPIs + trend + yearly history). */
  getNational: (init?: RequestInit) =>
    get<CityDetail>("/api/v1/national", {}, init),

  /** France-wide per-type (Maison / Appartement) price aggregate. */
  listNationalHousing: (init?: RequestInit) =>
    get<Page<HousingPriceByType>>("/api/v1/national/housing", {}, init),

  /** Per-type (Maison / Appartement) price metrics. */
  listHousingPrices: (params: ListHousingPricesParams = {}, init?: RequestInit) =>
    get<Page<HousingPriceByType>>("/api/v1/housing/prices", params, init),

  /** Arrondissements of Paris/Lyon/Marseille (intra-city drill-down). */
  listArrondissements: (params: ListArrondissementsParams = {}, init?: RequestInit) =>
    get<Page<ArrondissementMetrics>>("/api/v1/arrondissements", params, init),

  /** Single arrondissement detail + per-year history. */
  getArrondissement: (code: string, init?: RequestInit) =>
    get<ArrondissementDetail>(
      `/api/v1/arrondissements/${encodeURIComponent(code)}`,
      {},
      init,
    ),

  /** Geolocated train stations (map point layer). */
  listGares: (params: ListGaresParams = {}, init?: RequestInit) =>
    get<Page<Gare>>("/api/v1/mobility/gares", params, init),
};

export type Api = typeof api;
