// Personalized matching engine for the "young active buying in Paris" persona.
//
// Turns the enriched Gold commune row (price/affordability + rail + amenities +
// demographics) into a single 0–100 match score, driven by the user's criteria
// and their weighting of what matters. Pure functions, no I/O — used both to
// color the map and to rank the recommendation list.

import type { CityMetrics } from "./api";

// --- Categorical ladders (Gold class labels -> ordinal 0..1) ----------------

export const DESSERTE_LEVELS = [
  "Non desservie",
  "Desservie",
  "Bien desservie",
  "Hub majeur",
] as const;
export type DesserteLevel = (typeof DESSERTE_LEVELS)[number];

const DESSERTE_SCORE: Record<string, number> = {
  "Hub majeur": 1,
  "Bien desservie": 0.8,
  Desservie: 0.55,
  "Non desservie": 0.1,
};

export const EQUIPEMENT_LEVELS = [
  "Sous-équipée",
  "Équipée",
  "Bien équipée",
  "Très équipée",
] as const;
export type EquipementLevel = (typeof EQUIPEMENT_LEVELS)[number];

const EQUIPEMENT_SCORE: Record<string, number> = {
  "Très équipée": 1,
  "Bien équipée": 0.75,
  Équipée: 0.5,
  "Sous-équipée": 0.2,
};

// Affordability fallback when the user hasn't entered a budget yet.
const AFFORDABILITY_SCORE: Record<string, number> = {
  "Très abordable": 1,
  Abordable: 0.8,
  Tendu: 0.45,
  "Très tendu": 0.15,
};

// --- User inputs ------------------------------------------------------------

/** How much each dimension counts (0–100 sliders). */
export type Weights = {
  budget: number;
  transport: number;
  services: number;
  jeune: number;
};

export const DEFAULT_WEIGHTS: Weights = {
  budget: 60,
  transport: 50,
  services: 40,
  jeune: 30,
};

export type Criteria = {
  /** Total purchase budget, €. */
  budgetTotal: number | null;
  /** Desired living area, m². */
  surface: number | null;
  /** Hard filter: minimum rail-service level. */
  desserteMin: DesserteLevel | "";
  /** Hard filter: max distance to nearest station, km. */
  distanceGareMax: number | null;
  /** Hard filter: minimum amenity level. */
  equipementMin: EquipementLevel | "";
};

export const DEFAULT_CRITERIA: Criteria = {
  budgetTotal: null,
  surface: null,
  desserteMin: "",
  distanceGareMax: null,
  equipementMin: "",
};

const clamp01 = (x: number) => Math.max(0, Math.min(1, x));

/** Communes that have an arrondissement breakdown (drill-down targets). */
export const DRILLABLE_COMMUNES: Record<string, string> = {
  "75056": "75", // Paris
  "69123": "69", // Lyon
  "13055": "13", // Marseille
};

// --- Per-dimension sub-scores (0..1) ----------------------------------------

/**
 * Budget fit. With a budget+surface the user states a target €/m²; we reward
 * communes priced under it (and lightly under-reward the unaffordable ones).
 * Without a budget, fall back to the ETL's affordability class.
 */
function budgetScore(c: CityMetrics, crit: Criteria): number | null {
  const prix = c.prix_m2_median;
  if (prix == null) return null;
  const target = targetPricePerM2(crit);
  if (target == null) {
    return c.affordability_class != null
      ? AFFORDABILITY_SCORE[c.affordability_class] ?? null
      : null;
  }
  // ratio 1 = exactly on budget; >1 = cheaper (better), <1 = over budget.
  const ratio = target / prix;
  // 0.6×budget -> 0, on-budget -> ~0.7, 1.5×headroom -> 1.
  return clamp01((ratio - 0.6) / 0.9);
}

function transportScore(c: CityMetrics): number | null {
  if (c.desserte_class == null) return null;
  let s = DESSERTE_SCORE[c.desserte_class] ?? 0.1;
  // Soft penalty when the nearest station is far (>2 km starts to bite).
  if (c.distance_gare_km != null && c.distance_gare_km > 2) {
    s -= Math.min(0.4, (c.distance_gare_km - 2) * 0.05);
  }
  return clamp01(s);
}

function servicesScore(c: CityMetrics): number | null {
  if (c.niveau_equipement == null) return null;
  return EQUIPEMENT_SCORE[c.niveau_equipement] ?? null;
}

/** Share of under-65 ("active") population, with a nod to the under-25s. */
function jeuneScore(c: CityMetrics): number | null {
  if (c.pct_25_64 == null && c.pct_moins25 == null) return null;
  const actifs = (c.pct_25_64 ?? 0) + (c.pct_moins25 ?? 0);
  // 50% -> 0, 85% -> 1 (Paris hovers ~82%).
  return clamp01((actifs - 50) / 35);
}

// --- Composite --------------------------------------------------------------

export type ScoreBreakdown = {
  score: number; // 0..100, null-dimensions excluded from the weighting
  sub: { budget: number | null; transport: number | null; services: number | null; jeune: number | null };
  surfaceAtteignable: number | null; // m² buyable for the budget at local price
  passesFilters: boolean;
};

/** A Gold commune row augmented with its match result (map + list view-model). */
export type ScoredCity = CityMetrics & { match: ScoreBreakdown };

/** Score every commune and sort best-match first. */
export function rankCities(
  cities: CityMetrics[],
  crit: Criteria,
  weights: Weights,
): ScoredCity[] {
  return cities
    .map((c) => ({ ...c, match: scoreCity(c, crit, weights) }))
    .sort((a, b) => b.match.score - a.match.score);
}

/** €/m² the user can afford for the desired surface (needs both inputs). */
export function targetPricePerM2(crit: Criteria): number | null {
  if (crit.budgetTotal == null || crit.surface == null || crit.surface <= 0) {
    return null;
  }
  return crit.budgetTotal / crit.surface;
}

/** Hard filters: a commune is kept only if it clears every active criterion. */
export function passesCriteria(c: CityMetrics, crit: Criteria): boolean {
  if (crit.desserteMin) {
    const need = DESSERTE_LEVELS.indexOf(crit.desserteMin);
    const have = c.desserte_class
      ? DESSERTE_LEVELS.indexOf(c.desserte_class as DesserteLevel)
      : -1;
    if (have < need) return false;
  }
  if (crit.equipementMin) {
    const need = EQUIPEMENT_LEVELS.indexOf(crit.equipementMin);
    const have = c.niveau_equipement
      ? EQUIPEMENT_LEVELS.indexOf(c.niveau_equipement as EquipementLevel)
      : -1;
    if (have < need) return false;
  }
  if (crit.distanceGareMax != null) {
    if (c.distance_gare_km == null || c.distance_gare_km > crit.distanceGareMax) {
      return false;
    }
  }
  return true;
}

export function scoreCity(
  c: CityMetrics,
  crit: Criteria,
  weights: Weights,
): ScoreBreakdown {
  const sub = {
    budget: budgetScore(c, crit),
    transport: transportScore(c),
    services: servicesScore(c),
    jeune: jeuneScore(c),
  };
  const parts: [number | null, number][] = [
    [sub.budget, weights.budget],
    [sub.transport, weights.transport],
    [sub.services, weights.services],
    [sub.jeune, weights.jeune],
  ];
  let wsum = 0;
  let acc = 0;
  for (const [value, w] of parts) {
    if (value == null || w <= 0) continue;
    acc += value * w;
    wsum += w;
  }
  const score = wsum > 0 ? Math.round((acc / wsum) * 100) : 0;
  const target = c.prix_m2_median;
  return {
    score,
    sub,
    surfaceAtteignable:
      crit.budgetTotal != null && target != null && target > 0
        ? Math.round(crit.budgetTotal / target)
        : null,
    passesFilters: passesCriteria(c, crit),
  };
}

// --- Department aggregation (France-scope choropleth) -----------------------

function mean(values: (number | null | undefined)[]): number | null {
  let sum = 0;
  let n = 0;
  for (const v of values) {
    if (v != null) {
      sum += v;
      n += 1;
    }
  }
  return n ? sum / n : null;
}

/** Most frequent non-null value (for categorical class fields). */
function modal<T>(values: (T | null | undefined)[]): T | null {
  const counts = new Map<T, number>();
  for (const v of values) {
    if (v == null) continue;
    counts.set(v, (counts.get(v) ?? 0) + 1);
  }
  let best: T | null = null;
  let bestN = 0;
  for (const [v, n] of counts) {
    if (n > bestN) {
      best = v;
      bestN = n;
    }
  }
  return best;
}

/**
 * Collapse scored communes into one synthetic ScoredCity per department, so the
 * France map renders a department choropleth with the SAME color scales as the
 * commune view (continuous fields are averaged, class fields take the mode).
 * Keyed by department code; `code_commune` is set to that code so it slots into
 * the existing choropleth lookup unchanged.
 */
export function aggregateByDepartement(
  cities: ScoredCity[],
): Map<string, ScoredCity> {
  const groups = new Map<string, ScoredCity[]>();
  for (const c of cities) {
    if (!c.code_departement) continue;
    const g = groups.get(c.code_departement);
    if (g) g.push(c);
    else groups.set(c.code_departement, [c]);
  }
  const out = new Map<string, ScoredCity>();
  for (const [dep, group] of groups) {
    out.set(dep, {
      ...group[0],
      code_commune: dep,
      nom_commune: dep,
      prix_m2_median: mean(group.map((c) => c.prix_m2_median)),
      pct_25_64: mean(group.map((c) => c.pct_25_64)),
      pct_moins25: mean(group.map((c) => c.pct_moins25)),
      affordability_class: modal(group.map((c) => c.affordability_class)),
      desserte_class: modal(group.map((c) => c.desserte_class)),
      niveau_equipement: modal(group.map((c) => c.niveau_equipement)),
      match: {
        ...group[0].match,
        score: Math.round(mean(group.map((c) => c.match.score)) ?? 0),
        passesFilters: true,
      },
    });
  }
  return out;
}

// --- Color scales (shared by map + legend) ----------------------------------

/** Green→amber→red by match score (higher = better fit). */
export function scoreColor(score: number): string {
  if (score >= 75) return "#16a34a";
  if (score >= 55) return "#84cc16";
  if (score >= 40) return "#f59e0b";
  if (score >= 25) return "#f97316";
  return "#ef4444";
}

export const AFFORDABILITY_COLOR: Record<string, string> = {
  "Très abordable": "#16a34a",
  Abordable: "#84cc16",
  Tendu: "#f59e0b",
  "Très tendu": "#ef4444",
};

export const DESSERTE_COLOR: Record<string, string> = {
  "Hub majeur": "#4338ca",
  "Bien desservie": "#6366f1",
  Desservie: "#a5b4fc",
  "Non desservie": "#cbd5e1",
};

export const EQUIPEMENT_COLOR: Record<string, string> = {
  "Très équipée": "#16a34a",
  "Bien équipée": "#84cc16",
  Équipée: "#f59e0b",
  "Sous-équipée": "#ef4444",
};
