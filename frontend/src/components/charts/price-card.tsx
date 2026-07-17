"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  XAxis,
} from "recharts";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { Card, CardHeader, ReportButton } from "@/components/ui/card";
import type { CityDetail } from "@/lib/api";
import { formatPrixM2, monthlyPriceBars, priceDeltaPct } from "@/lib/mock";

export function PriceCard({ detail }: { detail: CityDetail }) {
  const bars = monthlyPriceBars(detail);
  const delta = priceDeltaPct(detail);
  const positive = (delta ?? 0) >= 0;
  const Arrow = positive ? ArrowUpRight : ArrowDownRight;

  return (
    <Card>
      <CardHeader
        title={
          <p className="text-sm font-medium text-muted">
            Prix médian au m² - {detail.nom_commune}
          </p>
        }
        action={<ReportButton />}
      />

      <div className="mb-1 text-2xl font-bold tracking-tight">
        {formatPrixM2(detail.prix_m2_median)}
      </div>
      {delta != null && (
        <div
          className={`mb-1 flex items-center gap-1 text-sm font-medium ${
            positive ? "text-success" : "text-red-500"
          }`}
        >
          <Arrow size={16} />
          {Math.abs(delta).toFixed(1)}%
          <span className="font-normal text-muted">vs mois précédent</span>
        </div>
      )}
      <p className="mb-4 text-xs text-muted">Évolution mensuelle du prix médian</p>

      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={bars} barGap={2} barCategoryGap="20%">
          <CartesianGrid vertical={false} stroke="#eceef3" strokeDasharray="4 4" />
          <XAxis
            dataKey="month"
            tickLine={false}
            axisLine={false}
            tick={{ fill: "#8a8f9c", fontSize: 11 }}
          />
          <Bar dataKey="current" fill="#5d5fef" radius={[4, 4, 0, 0]} barSize={8} />
          <Bar dataKey="previous" fill="#e6e8f0" radius={[4, 4, 0, 0]} barSize={8} />
        </BarChart>
      </ResponsiveContainer>

      <div className="mt-4 flex items-center gap-6 text-xs text-muted">
        <Legend color="#5d5fef" label="Année en cours" />
        <Legend color="#e6e8f0" label="Année précédente" />
      </div>
    </Card>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-2">
      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}
