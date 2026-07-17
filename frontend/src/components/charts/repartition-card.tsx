"use client";

import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";
import { Card, CardHeader, ReportButton } from "@/components/ui/card";
import type { HousingPriceByType } from "@/lib/api";
import { housingTypeDonut } from "@/lib/mock";

export function RepartitionCard({ rows }: { rows: HousingPriceByType[] }) {
  const segments = housingTypeDonut(rows);
  const total = segments.reduce((sum, s) => sum + s.value, 0);
  return (
    <Card>
      <CardHeader
        title={
          <div>
            <p className="text-sm font-semibold">Répartition par type</p>
            <p className="text-xs text-muted">Transactions par type de bien</p>
          </div>
        }
        action={<ReportButton />}
      />

      <div className="relative">
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={segments}
              dataKey="value"
              nameKey="name"
              innerRadius={58}
              outerRadius={85}
              paddingAngle={3}
              startAngle={90}
              endAngle={-270}
              stroke="none"
            >
              {segments.map((s) => (
                <Cell key={s.name} fill={s.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>

        {/* Tooltip-style badge: total transactions */}
        <div className="pointer-events-none absolute right-4 top-8 rounded-xl bg-ink px-3 py-2 text-bg shadow-lg">
          <p className="text-[10px] opacity-70">Total</p>
          <p className="text-sm font-semibold">
            {total.toLocaleString("fr-FR")} ventes
          </p>
        </div>
      </div>

      <div className="mt-2 flex items-center justify-around text-xs">
        {segments.map((s) => (
          <div key={s.name} className="flex flex-col items-center gap-1">
            <span className="flex items-center gap-1.5 text-muted">
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: s.color }}
              />
              {s.name}
            </span>
            <span className="font-semibold">
              {total ? Math.round((s.value / total) * 100) : 0}%
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}
