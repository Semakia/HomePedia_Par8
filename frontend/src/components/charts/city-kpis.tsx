import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import type { CityDetail } from "@/lib/api";
import { formatPrixM2, priceDeltaPct } from "@/lib/mock";
import { AFFORDABILITY_COLOR, DESSERTE_COLOR } from "@/lib/scoring";

/**
 * Headline indicators for the selected city (top of the stats page).
 * In `national` (France-wide) mode the commune-level categorical indicators
 * (affordability / rail service / amenities) are hidden — they aggregate to a
 * misleading modal class at country scale — leaving the meaningful totals.
 */
export function CityKpis({
  detail,
  national = false,
}: {
  detail: CityDetail;
  national?: boolean;
}) {
  const delta = priceDeltaPct(detail);

  return (
    <div
      className={`grid grid-cols-2 gap-3 sm:grid-cols-3 ${
        national ? "lg:grid-cols-3" : "lg:grid-cols-6"
      }`}
    >
      <Kpi label="Prix médian" value={formatPrixM2(detail.prix_m2_median)}>
        {delta != null && <Delta value={delta} />}
      </Kpi>

      {!national && (
        <Kpi
          label="Abordabilité"
          value={detail.affordability_class ?? "—"}
          valueColor={
            detail.affordability_class
              ? AFFORDABILITY_COLOR[detail.affordability_class]
              : undefined
          }
          sub={
            detail.affordability_years != null
              ? `${detail.affordability_years} ans de revenu`
              : undefined
          }
        />
      )}

      <Kpi
        label="Revenu médian"
        value={
          detail.revenu_median != null
            ? `${Math.round(detail.revenu_median).toLocaleString("fr-FR")} €`
            : "—"
        }
      />

      <Kpi
        label="Population"
        value={
          detail.population != null
            ? detail.population.toLocaleString("fr-FR")
            : "—"
        }
      />

      {!national && (
        <Kpi
          label="Desserte"
          value={detail.desserte_class ?? "—"}
          valueColor={
            detail.desserte_class
              ? DESSERTE_COLOR[detail.desserte_class]
              : undefined
          }
          sub={
            detail.nb_gares != null ? `${detail.nb_gares} gare(s)` : undefined
          }
        />
      )}

      {!national && (
        <Kpi label="Équipement" value={detail.niveau_equipement ?? "—"} />
      )}
    </div>
  );
}

function Kpi({
  label,
  value,
  valueColor,
  sub,
  children,
}: {
  label: string;
  value: string;
  valueColor?: string;
  sub?: string;
  children?: React.ReactNode;
}) {
  return (
    <Card className="!p-4">
      <p className="text-xs text-muted">{label}</p>
      <p
        className="mt-1 truncate text-base font-semibold"
        style={valueColor ? { color: valueColor } : undefined}
        title={value}
      >
        {value}
      </p>
      {sub && <p className="text-[11px] text-muted">{sub}</p>}
      {children}
    </Card>
  );
}

function Delta({ value }: { value: number }) {
  const positive = value >= 0;
  const Arrow = positive ? ArrowUpRight : ArrowDownRight;
  return (
    <span
      className={`mt-0.5 flex items-center gap-0.5 text-xs font-medium ${
        positive ? "text-success" : "text-red-500"
      }`}
    >
      <Arrow size={13} />
      {Math.abs(value).toFixed(1)}%
      <span className="font-normal text-muted">vs mois préc.</span>
    </span>
  );
}
