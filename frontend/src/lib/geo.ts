// Geographic helpers shared by client and server (no "server-only" here).

import type { FeatureCollection } from "geojson";

/** Île-de-France department codes — the map's default scope. */
export const IDF_DEPARTEMENTS = ["75", "77", "78", "91", "92", "93", "94", "95"];

/** [southWest, northEast] corners, as [lat, lng]. */
export type BBox = [[number, number], [number, number]];

// Fixed framing boxes so the map centers on the whole scope regardless of which
// communes the API happens to return (fitting to data points alone can drift
// Paris-centric when outer departments are sparse).
/** Île-de-France region (all 8 departments). */
export const IDF_BOUNDS: BBox = [
  [48.1, 1.4],
  [49.25, 3.6],
];
/** Metropolitan France (incl. Corsica). */
export const FRANCE_BOUNDS: BBox = [
  [41, -5.5],
  [51.5, 9.8],
];

// Commune boundary polygons come from the official French government API
// (geo.api.gouv.fr, CORS-enabled). Fetched once per scope and memoized for the
// session — boundaries don't change between renders.
const contourCache = new Map<string, Promise<FeatureCollection>>();

async function fetchDeptContours(dep: string): Promise<FeatureCollection> {
  const url = `https://geo.api.gouv.fr/communes?codeDepartement=${dep}&fields=code,nom&format=geojson&geometry=contour`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`contours ${dep}: HTTP ${res.status}`);
  return (await res.json()) as FeatureCollection;
}

// Department boundary polygons (metropolitan France, ~96), bundled in
// public/geo so the France-scope choropleth has no external runtime dependency.
// Source: gregoiredavid/france-geojson (simplified); properties = {code, nom}.
let deptContours: Promise<FeatureCollection> | null = null;

/** Department contours for the France-scope choropleth (memoized). */
export function fetchDepartementContours(): Promise<FeatureCollection> {
  if (!deptContours) {
    deptContours = fetch("/geo/departements.geojson").then((res) => {
      if (!res.ok) throw new Error(`dept contours: HTTP ${res.status}`);
      return res.json() as Promise<FeatureCollection>;
    });
    deptContours.catch(() => {
      deptContours = null; // let a later attempt retry
    });
  }
  return deptContours;
}

/** Merged commune contours for several departments (browser-side). */
export function fetchContours(departements: string[]): Promise<FeatureCollection> {
  const key = [...departements].sort().join(",");
  let pending = contourCache.get(key);
  if (!pending) {
    pending = Promise.all(departements.map(fetchDeptContours)).then((fcs) => ({
      type: "FeatureCollection" as const,
      features: fcs.flatMap((fc) => fc.features),
    }));
    // Don't cache a rejected fetch — let a later attempt retry.
    pending.catch(() => contourCache.delete(key));
    contourCache.set(key, pending);
  }
  return pending;
}
