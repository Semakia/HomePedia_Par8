import type {
  ArrondissementMetrics,
  CityDetail,
  CityMetrics,
  Gare,
  HousingPriceByType,
  PriceTrendPoint,
} from "./api";

// --- Contract aliases (single source of truth = generated OpenAPI types) ----
export type { CityMetrics, CityDetail, PriceTrendPoint, HousingPriceByType };

export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
};

function page<T>(items: T[]): Page<T> {
  return { items, total: items.length, page: 1, size: 50, pages: 1 };
}

// --- Mock data shaped EXACTLY like the (enriched) Gold API responses ---------
// Used only as a fallback when the live API is unreachable. Values are plausible
// so the matching score still behaves in offline/mock mode. Île-de-France focus
// to match the product's default map scope.

type CityInput = Partial<CityMetrics> &
  Pick<CityMetrics, "code_commune" | "nom_commune" | "code_departement">;

/** Build a full CityMetrics row, defaulting the many nullable fields to null. */
function city(input: CityInput): CityMetrics {
  return {
    year: 2024,
    region: "Île-de-France",
    population: null,
    insee_ref_year: 2022,
    revenu_median: null,
    revenu_ref_year: 2023,
    prix_m2_median: null,
    prix_m2_mean: null,
    surface_median: null,
    nb_transactions: 0,
    longitude: null,
    latitude: null,
    type_commune: null,
    affordability_years: null,
    m2_par_an: null,
    affordability_class: null,
    nb_gares: null,
    distance_gare_km: null,
    gare_proche_nom: null,
    desserte_class: null,
    niveau_equipement: null,
    nb_total_equipements: null,
    nb_sante: null,
    nb_commerces: null,
    nb_enseignement: null,
    nb_supermarche: null,
    pct_moins25: null,
    pct_25_64: null,
    pct_65plus: null,
    ...input,
  };
}

export const cities: CityMetrics[] = [
  city({ code_commune: "75056", nom_commune: "Paris", code_departement: "75", revenu_median: 33650, prix_m2_median: 9562, prix_m2_mean: 9778, surface_median: 42, nb_transactions: 24551, longitude: 2.3412, latitude: 48.8612, population: 2113705, type_commune: "Grande ville", affordability_years: 19.9, m2_par_an: 3.5, affordability_class: "Très tendu", nb_gares: 28, distance_gare_km: 0, desserte_class: "Hub majeur", niveau_equipement: "Très équipée", nb_total_equipements: 258642, nb_sante: 57000, nb_commerces: 54174, nb_enseignement: 5618, nb_supermarche: 1434, pct_moins25: 26.86, pct_25_64: 55.64, pct_65plus: 17.5 }),
  city({ code_commune: "92050", nom_commune: "Montrouge", code_departement: "92", revenu_median: 30100, prix_m2_median: 8200, prix_m2_mean: 8350, surface_median: 48, nb_transactions: 540, longitude: 2.3147, latitude: 48.8189, population: 50118, type_commune: "Ville moyenne", affordability_years: 16.8, m2_par_an: 3.7, affordability_class: "Tendu", nb_gares: 1, distance_gare_km: 0.4, desserte_class: "Bien desservie", niveau_equipement: "Très équipée", nb_total_equipements: 4200, nb_sante: 820, nb_commerces: 760, nb_enseignement: 90, nb_supermarche: 28, pct_moins25: 27.4, pct_25_64: 58.1, pct_65plus: 14.5 }),
  city({ code_commune: "93066", nom_commune: "Saint-Denis", code_departement: "93", revenu_median: 17200, prix_m2_median: 4350, prix_m2_mean: 4520, surface_median: 55, nb_transactions: 920, longitude: 2.3568, latitude: 48.9362, population: 113116, type_commune: "Ville moyenne", affordability_years: 12.4, m2_par_an: 4.0, affordability_class: "Abordable", nb_gares: 3, distance_gare_km: 0.3, desserte_class: "Bien desservie", niveau_equipement: "Très équipée", nb_total_equipements: 6100, nb_sante: 1100, nb_commerces: 980, nb_enseignement: 160, nb_supermarche: 36, pct_moins25: 38.2, pct_25_64: 52.4, pct_65plus: 9.4 }),
  city({ code_commune: "94028", nom_commune: "Créteil", code_departement: "94", revenu_median: 20800, prix_m2_median: 4180, prix_m2_mean: 4310, surface_median: 60, nb_transactions: 760, longitude: 2.4556, latitude: 48.7905, population: 92897, type_commune: "Ville moyenne", affordability_years: 12.1, m2_par_an: 4.9, affordability_class: "Abordable", nb_gares: 2, distance_gare_km: 0.6, desserte_class: "Bien desservie", niveau_equipement: "Très équipée", nb_total_equipements: 5400, nb_sante: 1200, nb_commerces: 720, nb_enseignement: 150, nb_supermarche: 30, pct_moins25: 35.1, pct_25_64: 52.9, pct_65plus: 12.0 }),
  city({ code_commune: "78646", nom_commune: "Versailles", code_departement: "78", revenu_median: 32400, prix_m2_median: 6600, prix_m2_mean: 6820, surface_median: 65, nb_transactions: 610, longitude: 2.1301, latitude: 48.8049, population: 85416, type_commune: "Ville moyenne", affordability_years: 13.6, m2_par_an: 4.9, affordability_class: "Tendu", nb_gares: 3, distance_gare_km: 0.5, desserte_class: "Bien desservie", niveau_equipement: "Très équipée", nb_total_equipements: 5200, nb_sante: 1050, nb_commerces: 690, nb_enseignement: 140, nb_supermarche: 24, pct_moins25: 30.2, pct_25_64: 52.6, pct_65plus: 17.2 }),
  city({ code_commune: "91377", nom_commune: "Massy", code_departement: "91", revenu_median: 24600, prix_m2_median: 4050, prix_m2_mean: 4180, surface_median: 62, nb_transactions: 430, longitude: 2.2731, latitude: 48.7309, population: 50644, type_commune: "Ville moyenne", affordability_years: 10.2, m2_par_an: 6.1, affordability_class: "Très abordable", nb_gares: 2, distance_gare_km: 0.4, desserte_class: "Bien desservie", niveau_equipement: "Bien équipée", nb_total_equipements: 3100, nb_sante: 540, nb_commerces: 420, nb_enseignement: 80, nb_supermarche: 18, pct_moins25: 33.0, pct_25_64: 54.5, pct_65plus: 12.5 }),
  city({ code_commune: "95127", nom_commune: "Cergy", code_departement: "95", revenu_median: 21300, prix_m2_median: 3300, prix_m2_mean: 3420, surface_median: 64, nb_transactions: 480, longitude: 2.0378, latitude: 49.0361, population: 66285, type_commune: "Ville moyenne", affordability_years: 9.9, m2_par_an: 6.5, affordability_class: "Très abordable", nb_gares: 3, distance_gare_km: 0.5, desserte_class: "Bien desservie", niveau_equipement: "Très équipée", nb_total_equipements: 4300, nb_sante: 760, nb_commerces: 540, nb_enseignement: 120, nb_supermarche: 22, pct_moins25: 37.8, pct_25_64: 53.0, pct_65plus: 9.2 }),
  city({ code_commune: "77288", nom_commune: "Meaux", code_departement: "77", revenu_median: 19800, prix_m2_median: 2750, prix_m2_mean: 2860, surface_median: 66, nb_transactions: 390, longitude: 2.8782, latitude: 48.9601, population: 55750, type_commune: "Ville moyenne", affordability_years: 9.2, m2_par_an: 7.2, affordability_class: "Très abordable", nb_gares: 1, distance_gare_km: 0.6, desserte_class: "Desservie", niveau_equipement: "Bien équipée", nb_total_equipements: 3400, nb_sante: 620, nb_commerces: 470, nb_enseignement: 95, nb_supermarche: 20, pct_moins25: 36.5, pct_25_64: 51.8, pct_65plus: 11.7 }),
  city({ code_commune: "92012", nom_commune: "Boulogne-Billancourt", code_departement: "92", revenu_median: 35900, prix_m2_median: 8800, prix_m2_mean: 9050, surface_median: 50, nb_transactions: 880, longitude: 2.2399, latitude: 48.8356, population: 121334, type_commune: "Ville moyenne", affordability_years: 16.9, m2_par_an: 4.1, affordability_class: "Tendu", nb_gares: 2, distance_gare_km: 0.4, desserte_class: "Bien desservie", niveau_equipement: "Très équipée", nb_total_equipements: 7100, nb_sante: 1500, nb_commerces: 1020, nb_enseignement: 180, nb_supermarche: 34, pct_moins25: 28.9, pct_25_64: 56.2, pct_65plus: 14.9 }),
  city({ code_commune: "93048", nom_commune: "Montreuil", code_departement: "93", revenu_median: 22100, prix_m2_median: 6100, prix_m2_mean: 6280, surface_median: 52, nb_transactions: 970, longitude: 2.4416, latitude: 48.8638, population: 111240, type_commune: "Ville moyenne", affordability_years: 14.3, m2_par_an: 4.3, affordability_class: "Tendu", nb_gares: 2, distance_gare_km: 0.5, desserte_class: "Bien desservie", niveau_equipement: "Très équipée", nb_total_equipements: 6300, nb_sante: 1180, nb_commerces: 880, nb_enseignement: 165, nb_supermarche: 30, pct_moins25: 32.7, pct_25_64: 55.6, pct_65plus: 11.7 }),
];

export const citiesPage: Page<CityMetrics> = page(cities);

// Monthly price trend for Paris over two years (drives the comparison bars).
const PARIS_PRIX_2024 = [9800, 9950, 10100, 10250, 10180, 10320, 10410, 10380, 10500, 10460, 10620, 10750];
const PARIS_PRIX_2023 = [9200, 9300, 9250, 9400, 9380, 9450, 9500, 9480, 9550, 9520, 9600, 9650];
const PARIS_TX_2024 = [120, 145, 160, 150, 170, 185, 140, 130, 165, 155, 180, 190];

function buildParisTrend(): PriceTrendPoint[] {
  const points: PriceTrendPoint[] = [];
  for (let m = 0; m < 12; m++) {
    points.push({ year: 2023, month: m + 1, prix_m2_median: PARIS_PRIX_2023[m], nb_transactions: 0 });
    points.push({ year: 2024, month: m + 1, prix_m2_median: PARIS_PRIX_2024[m], nb_transactions: PARIS_TX_2024[m] });
  }
  return points;
}

// Per-year headline history (oldest -> latest), latest mirrors the cities[0] row.
const parisMetricsByYear: CityDetail["metrics_by_year"] = [
  { year: 2023, prix_m2_median: 9425, prix_m2_mean: 9480, surface_median: 42, nb_transactions: 21640 },
  { year: 2024, prix_m2_median: 9562, prix_m2_mean: 9778, surface_median: 42, nb_transactions: 24551 },
];

export const parisDetail: CityDetail = {
  ...cities[0],
  metrics_by_year: parisMetricsByYear,
  trend: buildParisTrend(),
};

export const parisHousingByType: HousingPriceByType[] = [
  { code_commune: "75056", type_local: "Appartement", prix_m2_median: 9650, surface_median: 38, nb_transactions: 22600 },
  { code_commune: "75056", type_local: "Maison", prix_m2_median: 8900, surface_median: 95, nb_transactions: 270 },
];

export const housingPricesPage: Page<HousingPriceByType> = page(parisHousingByType);

// --- France-wide aggregate (offline fallback for the "France entière" view) --
// Mirrors the API's /national contract: quantities summed, prices/income
// transaction/population-weighted over the mock cities, classes = modal by
// transaction volume. The trend/history reuse Paris's monthly shape rescaled to
// the national price level so the reused stats cards render plausibly offline.
function weightedMean(
  pick: (c: CityMetrics) => number | null | undefined,
  weight: (c: CityMetrics) => number,
): number {
  let num = 0;
  let den = 0;
  for (const c of cities) {
    const v = pick(c);
    const w = weight(c);
    if (v != null && w > 0) {
      num += v * w;
      den += w;
    }
  }
  return den > 0 ? num / den : 0;
}

const sumBy = (pick: (c: CityMetrics) => number | null | undefined): number =>
  cities.reduce((s, c) => s + (pick(c) ?? 0), 0);

/** Most frequent class label, weighted by transaction volume. */
function modalClass(pick: (c: CityMetrics) => string | null | undefined): string | null {
  const tally = new Map<string, number>();
  for (const c of cities) {
    const k = pick(c);
    if (k) tally.set(k, (tally.get(k) ?? 0) + c.nb_transactions);
  }
  let best: string | null = null;
  let bestW = -1;
  for (const [k, w] of tally) {
    if (w > bestW) {
      best = k;
      bestW = w;
    }
  }
  return best;
}

const tx = (c: CityMetrics) => c.nb_transactions;
const pop = (c: CityMetrics) => c.population ?? 0;
const nationalPrix = Math.round(weightedMean((c) => c.prix_m2_median, tx));
const parisPrix = cities[0].prix_m2_median ?? nationalPrix;
const priceScale = parisPrix ? nationalPrix / parisPrix : 1;
const nationalTx = sumBy(tx);

const nationalTrend: PriceTrendPoint[] = buildParisTrend().map((p) => ({
  ...p,
  prix_m2_median:
    p.prix_m2_median != null ? Math.round(p.prix_m2_median * priceScale) : null,
}));

const nationalMetricsByYear: CityDetail["metrics_by_year"] = parisMetricsByYear.map(
  (m, i) => ({
    year: m.year,
    prix_m2_median:
      m.prix_m2_median != null ? Math.round(m.prix_m2_median * priceScale) : null,
    prix_m2_mean:
      m.prix_m2_mean != null ? Math.round(m.prix_m2_mean * priceScale) : null,
    surface_median: m.surface_median,
    // Split the summed volume across the two mock vintages (older lighter).
    nb_transactions: Math.round(nationalTx * (i === 0 ? 0.45 : 0.55)),
  }),
);

export const nationalDetail: CityDetail = {
  code_commune: "FR",
  year: 2024,
  nom_commune: "France entière",
  code_departement: "FR",
  region: null,
  population: sumBy(pop),
  insee_ref_year: 2022,
  revenu_median: Math.round(weightedMean((c) => c.revenu_median, pop)),
  revenu_ref_year: 2023,
  prix_m2_median: nationalPrix,
  prix_m2_mean: Math.round(weightedMean((c) => c.prix_m2_mean, tx)),
  surface_median: Math.round(weightedMean((c) => c.surface_median, tx)),
  nb_transactions: nationalTx,
  longitude: null,
  latitude: null,
  type_commune: null,
  affordability_years: Number(weightedMean((c) => c.affordability_years, pop).toFixed(1)),
  m2_par_an: Number(weightedMean((c) => c.m2_par_an, pop).toFixed(1)),
  affordability_class: modalClass((c) => c.affordability_class),
  nb_gares: sumBy((c) => c.nb_gares),
  distance_gare_km: null,
  gare_proche_nom: null,
  desserte_class: modalClass((c) => c.desserte_class),
  niveau_equipement: modalClass((c) => c.niveau_equipement),
  nb_total_equipements: sumBy((c) => c.nb_total_equipements),
  nb_sante: sumBy((c) => c.nb_sante),
  nb_commerces: sumBy((c) => c.nb_commerces),
  nb_enseignement: sumBy((c) => c.nb_enseignement),
  nb_supermarche: sumBy((c) => c.nb_supermarche),
  pct_moins25: Number(weightedMean((c) => c.pct_moins25, pop).toFixed(1)),
  pct_25_64: Number(weightedMean((c) => c.pct_25_64, pop).toFixed(1)),
  pct_65plus: Number(weightedMean((c) => c.pct_65plus, pop).toFixed(1)),
  metrics_by_year: nationalMetricsByYear,
  trend: nationalTrend,
};

export const nationalHousingByType: HousingPriceByType[] = [
  {
    code_commune: "FR",
    type_local: "Appartement",
    prix_m2_median: Math.round(nationalPrix * 1.05),
    surface_median: 45,
    nb_transactions: Math.round(nationalTx * 0.62),
  },
  {
    code_commune: "FR",
    type_local: "Maison",
    prix_m2_median: Math.round(nationalPrix * 0.72),
    surface_median: 95,
    nb_transactions: Math.round(nationalTx * 0.38),
  },
];

// Paris arrondissements (drill-down fallback). A representative subset.
function arr(input: Partial<ArrondissementMetrics> & Pick<ArrondissementMetrics, "code_arrondissement" | "nom_arrondissement">): ArrondissementMetrics {
  return {
    year: 2024, code_commune_parent: "75056", nom_commune_parent: "Paris",
    code_departement: "75", region: "Île-de-France", population: null,
    insee_ref_year: 2022, revenu_median: null, revenu_ref_year: 2023,
    prix_m2_median: null, prix_m2_mean: null, surface_median: null,
    nb_transactions: 0, longitude: null, latitude: null,
    type_commune: "Grande ville", affordability_years: null, m2_par_an: null,
    affordability_class: null, ...input,
  };
}

export const parisArrondissements: ArrondissementMetrics[] = [
  arr({ code_arrondissement: "75104", nom_arrondissement: "Paris 4e", prix_m2_median: 12400, surface_median: 40, revenu_median: 41200, population: 28088, longitude: 2.3575, latitude: 48.8546, affordability_years: 22.6, m2_par_an: 3.3, affordability_class: "Très tendu", nb_transactions: 410 }),
  arr({ code_arrondissement: "75111", nom_arrondissement: "Paris 11e", prix_m2_median: 10650, surface_median: 41, revenu_median: 33900, population: 147017, longitude: 2.3776, latitude: 48.8590, affordability_years: 20.1, m2_par_an: 3.2, affordability_class: "Très tendu", nb_transactions: 1620 }),
  arr({ code_arrondissement: "75116", nom_arrondissement: "Paris 16e", prix_m2_median: 10722, surface_median: 69, revenu_median: 49030, population: 159733, longitude: 2.2746, latitude: 48.8566, affordability_years: 15.3, m2_par_an: 4.6, affordability_class: "Tendu", nb_transactions: 1939 }),
  arr({ code_arrondissement: "75119", nom_arrondissement: "Paris 19e", prix_m2_median: 8600, surface_median: 44, revenu_median: 22600, population: 187015, longitude: 2.3820, latitude: 48.8870, affordability_years: 24.4, m2_par_an: 2.6, affordability_class: "Très tendu", nb_transactions: 1780 }),
  arr({ code_arrondissement: "75120", nom_arrondissement: "Paris 20e", prix_m2_median: 8950, surface_median: 43, revenu_median: 23800, population: 195814, longitude: 2.3984, latitude: 48.8634, affordability_years: 24.1, m2_par_an: 2.6, affordability_class: "Très tendu", nb_transactions: 1990 }),
];

// A few flagship Paris stations (gares layer fallback).
export const parisGares: Gare[] = [
  { code_uic: "87271007", nom_gare: "Paris Gare du Nord", code_commune: "75056", segment_drg: "A", frequentation: 257024152, frequentation_year: 2024, longitude: 2.355151, latitude: 48.880185 },
  { code_uic: "87384008", nom_gare: "Paris Saint-Lazare", code_commune: "75056", segment_drg: "A", frequentation: 114093491, frequentation_year: 2024, longitude: 2.325331, latitude: 48.876242 },
  { code_uic: "87113001", nom_gare: "Paris Est", code_commune: "75056", segment_drg: "A", frequentation: 42725621, frequentation_year: 2024, longitude: 2.358424, latitude: 48.876742 },
  { code_uic: "87686006", nom_gare: "Paris Montparnasse", code_commune: "75056", segment_drg: "A", frequentation: 51000000, frequentation_year: 2024, longitude: 2.320514, latitude: 48.840645 },
  { code_uic: "87547000", nom_gare: "Paris Gare de Lyon", code_commune: "75056", segment_drg: "A", frequentation: 110000000, frequentation_year: 2024, longitude: 2.373469, latitude: 48.844159 },
];

// --- UI selectors / view-models derived from the contract data --------------

export type MonthlyBar = { month: string; current: number | null; previous: number | null };

/** Group a city trend into per-month bars: latest year vs the year before. */
export function monthlyPriceBars(detail: CityDetail): MonthlyBar[] {
  const years = [...new Set(detail.trend.map((p) => p.year))].sort();
  const current = years.at(-1);
  const previous = years.at(-2);
  return Array.from({ length: 12 }, (_, i) => {
    const month = i + 1;
    const find = (y?: number) =>
      detail.trend.find((p) => p.year === y && p.month === month)?.prix_m2_median ?? null;
    return { month: String(month).padStart(2, "0"), current: find(current), previous: find(previous) };
  });
}

/** Percentage change between the last two available trend months. */
export function priceDeltaPct(detail: CityDetail): number | null {
  const pts = detail.trend.filter((p) => p.prix_m2_median != null);
  if (pts.length < 2) return null;
  const [prev, last] = [pts.at(-2)!, pts.at(-1)!];
  if (!prev.prix_m2_median) return null;
  return ((last.prix_m2_median! - prev.prix_m2_median) / prev.prix_m2_median) * 100;
}

export type DonutSegment = { name: string; value: number; color: string };

const TYPE_COLORS: Record<string, string> = {
  Appartement: "#5d5fef",
  Maison: "#a9aaf5",
};

/** Transactions share by dwelling type (contract-backed Répartition donut). */
export function housingTypeDonut(rows: HousingPriceByType[]): DonutSegment[] {
  return rows.map((r) => ({
    name: r.type_local,
    value: r.nb_transactions,
    color: TYPE_COLORS[r.type_local] ?? "#e6e7fb",
  }));
}

/** Marker color by price/m² tier (null → muted gray). */
export function markerColor(prixM2: number | null | undefined): string {
  if (prixM2 == null) return "#8a8f9c";
  if (prixM2 >= 6000) return "#ef4444";
  if (prixM2 >= 4000) return "#5d5fef";
  return "#22c55e";
}

/** Distinct department codes present in the dataset (for the filter select). */
export const departements: string[] = [
  ...new Set(cities.map((c) => c.code_departement)),
].sort();

/** Format a €/m² value for display, tolerating nulls. */
export function formatPrixM2(value: number | null | undefined): string {
  return value == null ? "—" : `${value.toLocaleString("fr-FR")} €/m²`;
}
