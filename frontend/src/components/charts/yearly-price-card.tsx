"use client";

import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardHeader } from "@/components/ui/card";
import type { CityDetail } from "@/lib/api";
import { forecastPrices } from "@/lib/forecast";

type Row = {
  year: string;
  prix: number | null;
  transactions: number | null;
  forecast: number | null;
};

/** Per-year median price (line) over transaction volume (bars), + a projection. */
export function YearlyPriceCard({ detail }: { detail: CityDetail }) {
  const hist = detail.metrics_by_year
    .filter((m) => m.prix_m2_median != null || m.nb_transactions != null)
    .map((m) => ({
      year: m.year,
      prix: m.prix_m2_median ?? null,
      transactions: m.nb_transactions ?? null,
    }))
    .sort((a, b) => a.year - b.year);

  const forecast = forecastPrices(
    hist.flatMap((h) => (h.prix != null ? [{ year: h.year, prix: h.prix }] : [])),
  );
  // Bridge the dashed line: the last real point also seeds the forecast series.
  const bridgeIdx = hist.reduce((idx, h, i) => (h.prix != null ? i : idx), -1);

  const data: Row[] = [
    ...hist.map((h, i) => ({
      year: String(h.year),
      prix: h.prix,
      transactions: h.transactions,
      forecast: forecast.length > 0 && i === bridgeIdx ? h.prix : null,
    })),
    ...forecast.map((f) => ({
      year: String(f.year),
      prix: null,
      transactions: null,
      forecast: f.prix,
    })),
  ];

  return (
    <Card>
      <CardHeader
        title={
          <div>
            <p className="text-sm font-semibold">Historique annuel</p>
            <p className="text-xs text-muted">
              Prix médian au m² et volume de transactions
            </p>
          </div>
        }
      />

      {data.length < 2 ? (
        <Empty />
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
            <CartesianGrid vertical={false} stroke="#eceef3" strokeDasharray="4 4" />
            <XAxis
              dataKey="year"
              tickLine={false}
              axisLine={false}
              tick={{ fill: "#8a8f9c", fontSize: 11 }}
            />
            <YAxis
              yAxisId="prix"
              tickLine={false}
              axisLine={false}
              width={48}
              tick={{ fill: "#8a8f9c", fontSize: 11 }}
              tickFormatter={(v: number) => `${Math.round(v / 1000)}k`}
            />
            <YAxis yAxisId="tx" orientation="right" hide />
            <Tooltip
              formatter={(value, name) =>
                name === "Prix médian"
                  ? [`${Number(value).toLocaleString("fr-FR")} €/m²`, name]
                  : [Number(value).toLocaleString("fr-FR"), name]
              }
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar
              yAxisId="tx"
              dataKey="transactions"
              name="Transactions"
              fill="#e6e8f0"
              radius={[4, 4, 0, 0]}
              barSize={28}
            />
            <Line
              yAxisId="prix"
              type="monotone"
              dataKey="prix"
              name="Prix médian"
              stroke="#5d5fef"
              strokeWidth={2.5}
              dot={{ r: 3 }}
            />
            <Line
              yAxisId="prix"
              type="monotone"
              dataKey="forecast"
              name="Projection"
              stroke="#f59e0b"
              strokeWidth={2}
              strokeDasharray="5 4"
              dot={{ r: 3 }}
              connectNulls
            />
          </ComposedChart>
        </ResponsiveContainer>
      )}

      {data.some((d) => d.forecast != null && d.prix == null) && (
        <p className="px-1 pt-1 text-[11px] text-muted">
          Projection indicative sur 3 ans (tendance linéaire de l&apos;historique)
          — ne tient pas compte des chocs de marché.
        </p>
      )}
    </Card>
  );
}

function Empty() {
  return (
    <div className="grid h-[220px] place-items-center text-sm text-muted">
      Donnée indisponible
    </div>
  );
}
