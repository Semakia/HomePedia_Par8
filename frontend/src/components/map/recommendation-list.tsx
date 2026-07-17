"use client";

import { Trophy } from "lucide-react";
import { formatPrixM2 } from "@/lib/mock";
import { scoreColor, type ScoredCity } from "@/lib/scoring";

/** Ranked best-match communes — the payoff of the criteria the user set. */
export function RecommendationList({
  cities,
  selectedId,
  onSelect,
}: {
  cities: ScoredCity[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const top = cities.slice(0, 12);

  return (
    <div className="flex h-full flex-col" data-tour="recommendations">
      <div className="mb-3 flex items-center gap-2">
        <Trophy size={16} className="text-primary" />
        <h2 className="text-sm font-semibold">Communes recommandées</h2>
      </div>

      {top.length === 0 ? (
        <p className="text-sm text-muted">Aucune commune ne correspond à vos critères.</p>
      ) : (
        <ol className="flex flex-col gap-2 overflow-y-auto pr-1">
          {top.map((c, i) => {
            const selected = c.code_commune === selectedId;
            return (
              <li key={c.code_commune}>
                <button
                  type="button"
                  onClick={() => onSelect(c.code_commune)}
                  className={`flex w-full items-center gap-3 rounded-xl border px-3 py-2.5 text-left transition-colors ${
                    selected
                      ? "border-primary/40 bg-primary-soft"
                      : "border-line hover:bg-bg"
                  }`}
                >
                  <span className="w-5 shrink-0 text-center text-sm font-semibold text-muted">
                    {i + 1}
                  </span>
                  <span
                    className="grid h-9 w-9 shrink-0 place-items-center rounded-full text-xs font-bold text-white"
                    style={{ backgroundColor: scoreColor(c.match.score) }}
                  >
                    {c.match.score}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium">
                      {c.nom_commune}
                    </span>
                    <span className="block text-xs text-muted">
                      {formatPrixM2(c.prix_m2_median)} · {c.code_departement}
                    </span>
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
