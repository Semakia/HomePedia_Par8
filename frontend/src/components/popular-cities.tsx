import { Card } from "@/components/ui/card";
import type { CityMetrics } from "@/lib/api";
import { formatPrixM2 } from "@/lib/mock";

const AVATAR_COLORS = ["#5d5fef", "#22c55e", "#f59e0b", "#ef4444"];

export function PopularCities({ cities }: { cities: CityMetrics[] }) {
  // Top communes by transaction volume (contract: CityMetrics).
  const top = [...cities]
    .sort((a, b) => b.nb_transactions - a.nb_transactions)
    .slice(0, 4);
  return (
    <Card>
      <h2 className="text-base font-semibold">Villes les plus populaires</h2>
      <p className="mb-5 text-xs text-muted">
        Communes avec le plus de transactions
      </p>

      <ul className="flex flex-col">
        {top.map((city, i) => (
          <li
            key={city.code_commune}
            className="flex items-center gap-3 border-b border-line py-3 last:border-0"
          >
            <span
              className="grid h-8 w-8 place-items-center rounded-full text-xs font-semibold text-white"
              style={{ backgroundColor: AVATAR_COLORS[i % AVATAR_COLORS.length] }}
            >
              {city.nom_commune[0]}
            </span>
            <span className="flex-1 text-sm font-medium">{city.nom_commune}</span>
            <span className="text-sm text-muted">
              {formatPrixM2(city.prix_m2_median)}
            </span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
