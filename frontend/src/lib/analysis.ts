// Rule-based textual analysis: turns a Gold CityDetail (price / affordability /
// rail / amenities / demographics / trend) into a human-readable written
// analysis — the "textual analysis" deliverable, deterministic and offline-safe
// (works on mock data too). No LLM: pure thresholds + templates so the output is
// stable and explainable. Comparisons use the national aggregate as a baseline.
import type { CityDetail } from "@/lib/api";

export type InsightTone = "positive" | "neutral" | "warning";
export type InsightCategory =
  | "affordability"
  | "market"
  | "transport"
  | "amenities"
  | "demographics"
  | "trend";

export type Insight = {
  category: InsightCategory;
  title: string;
  tone: InsightTone;
  body: string;
};

export type Analysis = {
  /** 2–3 sentence lead synthesis. */
  summary: string;
  insights: Insight[];
};

const nf = new Intl.NumberFormat("fr-FR");
const int = (v: number) => nf.format(Math.round(v));
const dec = (v: number) => nf.format(Math.round(v * 10) / 10);
const eur = (v: number) => `${int(v)} €/m²`;

// Percentage gap of `value` vs `ref`, rounded; null when either side is missing.
function gapPct(value?: number | null, ref?: number | null): number | null {
  if (value == null || ref == null || ref === 0) return null;
  return Math.round(((value - ref) / ref) * 100);
}

const AFFORDABILITY_TONE: Record<string, InsightTone> = {
  "Très abordable": "positive",
  Abordable: "positive",
  Tendu: "warning",
  "Très tendu": "warning",
};

const DESSERTE_TONE: Record<string, InsightTone> = {
  "Hub majeur": "positive",
  "Bien desservie": "positive",
  Desservie: "neutral",
  "Non desservie": "warning",
};

const EQUIPEMENT_TONE: Record<string, InsightTone> = {
  "Très équipée": "positive",
  "Bien équipée": "positive",
  Équipée: "neutral",
  "Sous-équipée": "warning",
};

/** First-vs-last price change over the last ≤12 months of the trend series. */
function trendChange(detail: CityDetail): { pct: number; months: number } | null {
  const points = [...detail.trend]
    .filter((p) => p.prix_m2_median != null)
    .sort((a, b) => a.year - b.year || a.month - b.month);
  if (points.length < 2) return null;
  const window = points.slice(-12);
  const first = window[0].prix_m2_median!;
  const last = window[window.length - 1].prix_m2_median!;
  if (first === 0) return null;
  return { pct: Math.round(((last - first) / first) * 100), months: window.length };
}

export function buildAnalysis(detail: CityDetail, reference?: CityDetail | null): Analysis {
  const insights: Insight[] = [];
  const ref = reference ?? null;

  // — Affordability —
  if (detail.affordability_class) {
    const years = detail.affordability_years;
    const refYears = ref?.affordability_years;
    let body = `Classé « ${detail.affordability_class} »`;
    if (years != null) {
      body += ` : il faut environ ${dec(years)} ans de revenu médian pour acquérir un bien type`;
      const g = years - (refYears ?? NaN);
      if (refYears != null && Math.abs(g) >= 0.5) {
        body += `, soit ${dec(Math.abs(g))} an${Math.abs(g) >= 2 ? "s" : ""} de ${g > 0 ? "plus" : "moins"} que la moyenne nationale`;
      }
    }
    insights.push({
      category: "affordability",
      title: "Abordabilité",
      tone: AFFORDABILITY_TONE[detail.affordability_class] ?? "neutral",
      body: body + ".",
    });
  }

  // — Market & price —
  if (detail.prix_m2_median != null) {
    const g = gapPct(detail.prix_m2_median, ref?.prix_m2_median);
    let body = `Le prix médian s'établit à ${eur(detail.prix_m2_median)}`;
    if (g != null && ref?.prix_m2_median != null) {
      body +=
        g === 0
          ? `, au niveau de la moyenne nationale`
          : `, soit ${Math.abs(g)} % ${g > 0 ? "au-dessus" : "en dessous"} de la moyenne nationale (${eur(ref.prix_m2_median)})`;
    }
    if (detail.nb_transactions) body += ` — ${int(detail.nb_transactions)} transactions recensées`;
    insights.push({
      category: "market",
      title: "Marché & prix",
      // For a buyer, cheaper than average is favourable.
      tone: g == null ? "neutral" : g > 5 ? "warning" : g < -5 ? "positive" : "neutral",
      body: body + ".",
    });
  }

  // — Transport —
  if (detail.desserte_class) {
    let body = `Desserte « ${detail.desserte_class} »`;
    if (detail.nb_gares != null) body += ` : ${int(detail.nb_gares)} gare${detail.nb_gares > 1 ? "s" : ""}`;
    if (detail.gare_proche_nom) {
      body += `, la plus proche étant ${detail.gare_proche_nom}`;
      if (detail.distance_gare_km != null) body += ` à ${dec(detail.distance_gare_km)} km`;
    }
    insights.push({
      category: "transport",
      title: "Transport",
      tone: DESSERTE_TONE[detail.desserte_class] ?? "neutral",
      body: body + ".",
    });
  }

  // — Amenities —
  if (detail.niveau_equipement) {
    const parts: string[] = [];
    if (detail.nb_commerces != null) parts.push(`${int(detail.nb_commerces)} commerces`);
    if (detail.nb_sante != null) parts.push(`${int(detail.nb_sante)} équipements de santé`);
    if (detail.nb_enseignement != null) parts.push(`${int(detail.nb_enseignement)} établissements d'enseignement`);
    const body = `Zone « ${detail.niveau_equipement} »${parts.length ? ` : ${parts.join(", ")}` : ""}.`;
    insights.push({
      category: "amenities",
      title: "Équipements",
      tone: EQUIPEMENT_TONE[detail.niveau_equipement] ?? "neutral",
      body,
    });
  }

  // — Demographics (young-active fit) —
  if (detail.pct_moins25 != null || detail.pct_25_64 != null) {
    const young = detail.pct_moins25 ?? 0;
    const active = detail.pct_25_64 ?? 0;
    // Share of under-45 is not available; use 25-64 as the "actifs" proxy.
    const profil =
      young >= 30 ? "jeune" : detail.pct_65plus != null && detail.pct_65plus >= 25 ? "plutôt âgé" : "équilibré";
    const fit = young >= 25 && active >= 45 ? "bien aligné" : "peu aligné";
    let body = "";
    if (detail.population != null) body += `${int(detail.population)} habitants. `;
    if (detail.pct_moins25 != null) body += `${dec(detail.pct_moins25)} % de moins de 25 ans`;
    if (detail.pct_25_64 != null) body += `${detail.pct_moins25 != null ? " et " : ""}${dec(detail.pct_25_64)} % de 25-64 ans`;
    body += ` : profil ${profil}, ${fit} avec une cible jeunes actifs.`;
    insights.push({
      category: "demographics",
      title: "Démographie",
      tone: fit === "bien aligné" ? "positive" : "neutral",
      body: body.trim(),
    });
  }

  // — Price trend —
  const tc = trendChange(detail);
  if (tc) {
    const verb = tc.pct > 0 ? "progressé" : tc.pct < 0 ? "reculé" : "stagné";
    const body = `Sur les ${tc.months} derniers mois, le prix médian a ${verb}${tc.pct !== 0 ? ` de ${Math.abs(tc.pct)} %` : ""}.`;
    insights.push({
      category: "trend",
      title: "Tendance",
      // Rising prices make buying harder → warning; falling → opportunity.
      tone: tc.pct > 3 ? "warning" : tc.pct < -3 ? "positive" : "neutral",
      body,
    });
  }

  return { summary: buildSummary(detail, ref, insights), insights };
}

function buildSummary(detail: CityDetail, ref: CityDetail | null, insights: Insight[]): string {
  const name = detail.nom_commune;
  const sentences: string[] = [];

  // Sentence 1: identity + affordability verdict.
  if (detail.affordability_class) {
    const adj: Record<string, string> = {
      "Très abordable": "un marché très abordable",
      Abordable: "un marché abordable",
      Tendu: "un marché tendu",
      "Très tendu": "un marché très tendu",
    };
    sentences.push(`${name} présente ${adj[detail.affordability_class] ?? "un marché contrasté"}`);
  } else {
    sentences.push(`${name} en un coup d'œil`);
  }

  // Sentence 2: price positioning.
  if (detail.prix_m2_median != null) {
    const g = gapPct(detail.prix_m2_median, ref?.prix_m2_median);
    if (g != null && Math.abs(g) >= 5) {
      sentences[0] += `, avec un prix médian ${Math.abs(g)} % ${g > 0 ? "au-dessus" : "en dessous"} de la moyenne nationale (${eur(detail.prix_m2_median)})`;
    } else {
      sentences[0] += `, à ${eur(detail.prix_m2_median)}`;
    }
  }
  sentences[0] += ".";

  // Sentence 3: livability headline (transport + amenities + demo).
  const bits: string[] = [];
  if (detail.desserte_class) bits.push(`desserte « ${detail.desserte_class.toLowerCase()} »`);
  if (detail.niveau_equipement) bits.push(`zone « ${detail.niveau_equipement.toLowerCase()} »`);
  const demo = insights.find((i) => i.category === "demographics");
  if (demo?.tone === "positive") bits.push("profil démographique adapté aux jeunes actifs");
  if (bits.length) {
    sentences.push(`Côté cadre de vie : ${bits.join(", ")}.`);
  }

  return sentences.join(" ");
}
