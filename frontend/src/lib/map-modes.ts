// Map coloring modes — single source of truth for the marker color AND the
// matching legend, so the two can never drift apart.

import type { CityMetrics } from "./api";
import {
  AFFORDABILITY_COLOR,
  DESSERTE_COLOR,
  EQUIPEMENT_COLOR,
  scoreColor,
  type ScoredCity,
} from "./scoring";

export type ColorMode =
  | "score"
  | "prix"
  | "abordabilite"
  | "transport"
  | "equipements"
  | "jeunes";

export const COLOR_MODES: { id: ColorMode; label: string }[] = [
  { id: "score", label: "Mon score" },
  { id: "prix", label: "Prix au m²" },
  { id: "abordabilite", label: "Abordabilité" },
  { id: "transport", label: "Transport" },
  { id: "equipements", label: "Équipements" },
  { id: "jeunes", label: "Jeunes actifs" },
];

const MUTED = "#cbd5e1";

function prixColor(prix: number | null | undefined): string {
  if (prix == null) return MUTED;
  if (prix >= 9000) return "#ef4444";
  if (prix >= 6500) return "#f97316";
  if (prix >= 4500) return "#f59e0b";
  if (prix >= 3000) return "#84cc16";
  return "#16a34a";
}

function jeunesColor(c: CityMetrics): string {
  const actifs = (c.pct_25_64 ?? 0) + (c.pct_moins25 ?? 0);
  if (c.pct_25_64 == null && c.pct_moins25 == null) return MUTED;
  if (actifs >= 85) return "#16a34a";
  if (actifs >= 80) return "#84cc16";
  if (actifs >= 75) return "#f59e0b";
  return "#f97316";
}

/** Resolve a marker color for the active mode. */
export function colorForCity(mode: ColorMode, c: ScoredCity): string {
  switch (mode) {
    case "score":
      return scoreColor(c.match.score);
    case "prix":
      return prixColor(c.prix_m2_median);
    case "abordabilite":
      return c.affordability_class
        ? AFFORDABILITY_COLOR[c.affordability_class] ?? MUTED
        : MUTED;
    case "transport":
      return c.desserte_class ? DESSERTE_COLOR[c.desserte_class] ?? MUTED : MUTED;
    case "equipements":
      return c.niveau_equipement
        ? EQUIPEMENT_COLOR[c.niveau_equipement] ?? MUTED
        : MUTED;
    case "jeunes":
      return jeunesColor(c);
  }
}

export type LegendItem = { color: string; label: string };

export function legendForMode(mode: ColorMode): LegendItem[] {
  switch (mode) {
    case "score":
      return [
        { color: "#16a34a", label: "Excellent (75+)" },
        { color: "#84cc16", label: "Bon (55–74)" },
        { color: "#f59e0b", label: "Moyen (40–54)" },
        { color: "#f97316", label: "Faible (25–39)" },
        { color: "#ef4444", label: "Hors cible (<25)" },
      ];
    case "prix":
      return [
        { color: "#16a34a", label: "< 3 000 €/m²" },
        { color: "#84cc16", label: "3–4,5 k€" },
        { color: "#f59e0b", label: "4,5–6,5 k€" },
        { color: "#f97316", label: "6,5–9 k€" },
        { color: "#ef4444", label: "> 9 000 €/m²" },
      ];
    case "abordabilite":
      return [
        { color: "#16a34a", label: "Très abordable" },
        { color: "#84cc16", label: "Abordable" },
        { color: "#f59e0b", label: "Tendu" },
        { color: "#ef4444", label: "Très tendu" },
      ];
    case "transport":
      return [
        { color: "#4338ca", label: "Hub majeur" },
        { color: "#6366f1", label: "Bien desservie" },
        { color: "#a5b4fc", label: "Desservie" },
        { color: "#cbd5e1", label: "Non desservie" },
      ];
    case "equipements":
      return [
        { color: "#16a34a", label: "Très équipée" },
        { color: "#84cc16", label: "Bien équipée" },
        { color: "#f59e0b", label: "Équipée" },
        { color: "#ef4444", label: "Sous-équipée" },
      ];
    case "jeunes":
      return [
        { color: "#16a34a", label: "≥ 85 % d'actifs" },
        { color: "#84cc16", label: "80–85 %" },
        { color: "#f59e0b", label: "75–80 %" },
        { color: "#f97316", label: "< 75 %" },
      ];
  }
}
