"use client";

import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";
import { Card, CardHeader } from "@/components/ui/card";
import type { CityDetail } from "@/lib/api";

const SEGMENTS = [
  { key: "pct_moins25", label: "− 25 ans", color: "#5d5fef" },
  { key: "pct_25_64", label: "25 – 64 ans", color: "#22c55e" },
  { key: "pct_65plus", label: "65 ans et +", color: "#f59e0b" },
] as const;

/** Age structure of the population (young-active fit for the persona). */
export function DemographicsCard({ detail }: { detail: CityDetail }) {
  const data = SEGMENTS.map((s) => ({
    label: s.label,
    color: s.color,
    value: detail[s.key] ?? 0,
  })).filter((s) => s.value > 0);

  const hasData =
    detail.pct_moins25 != null ||
    detail.pct_25_64 != null ||
    detail.pct_65plus != null;

  return (
    <Card>
      <CardHeader
        title={
          <div>
            <p className="text-sm font-semibold">Profil de population</p>
            <p className="text-xs text-muted">Répartition par âge</p>
          </div>
        }
      />

      {!hasData ? (
        <div className="grid h-[180px] place-items-center text-sm text-muted">
          Donnée indisponible
        </div>
      ) : (
        <>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                nameKey="label"
                innerRadius={52}
                outerRadius={80}
                paddingAngle={3}
                startAngle={90}
                endAngle={-270}
                stroke="none"
              >
                {data.map((s) => (
                  <Cell key={s.label} fill={s.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>

          <div className="mt-2 flex items-center justify-around text-xs">
            {data.map((s) => (
              <div key={s.label} className="flex flex-col items-center gap-1">
                <span className="flex items-center gap-1.5 text-muted">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: s.color }}
                  />
                  {s.label}
                </span>
                <span className="font-semibold">{s.value.toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </>
      )}
    </Card>
  );
}
