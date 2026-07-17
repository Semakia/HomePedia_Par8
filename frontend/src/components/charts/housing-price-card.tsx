"use client";

import { Card, CardHeader } from "@/components/ui/card";
import type { HousingPriceByType } from "@/lib/api";
import { formatPrixM2 } from "@/lib/mock";

const TYPE_COLORS: Record<string, string> = {
  Appartement: "#5d5fef",
  Maison: "#a9aaf5",
};

/** Median €/m² by dwelling type (Maison vs Appartement) — horizontal bars. */
export function HousingPriceCard({ rows }: { rows: HousingPriceByType[] }) {
  const priced = rows.filter((r) => r.prix_m2_median != null);
  const max = Math.max(1, ...priced.map((r) => r.prix_m2_median ?? 0));

  return (
    <Card>
      <CardHeader
        title={
          <div>
            <p className="text-sm font-semibold">Prix par type de bien</p>
            <p className="text-xs text-muted">Prix médian au m²</p>
          </div>
        }
      />

      {priced.length === 0 ? (
        <div className="grid h-[160px] place-items-center text-sm text-muted">
          Donnée indisponible
        </div>
      ) : (
        <div className="flex flex-col gap-4 pt-2">
          {priced.map((r) => (
            <div key={r.type_local} className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">{r.type_local}</span>
                <span className="tabular-nums text-muted">
                  {formatPrixM2(r.prix_m2_median)}
                </span>
              </div>
              <span className="h-2.5 w-full overflow-hidden rounded-full bg-line">
                <span
                  className="block h-full rounded-full"
                  style={{
                    width: `${((r.prix_m2_median ?? 0) / max) * 100}%`,
                    backgroundColor: TYPE_COLORS[r.type_local] ?? "#5d5fef",
                  }}
                />
              </span>
              {r.surface_median != null && (
                <span className="text-[11px] text-muted">
                  surface médiane {r.surface_median} m²
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
