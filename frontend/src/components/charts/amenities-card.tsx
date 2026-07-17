"use client";

import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardHeader } from "@/components/ui/card";
import type { CityDetail } from "@/lib/api";

const FIELDS = [
  { key: "nb_sante", label: "Santé", color: "#ef4444" },
  { key: "nb_commerces", label: "Commerces", color: "#5d5fef" },
  { key: "nb_enseignement", label: "Enseignement", color: "#22c55e" },
  { key: "nb_supermarche", label: "Supermarchés", color: "#f59e0b" },
] as const;

/** Facility counts (BPE) — quality-of-life amenities for the area. */
export function AmenitiesCard({ detail }: { detail: CityDetail }) {
  const data = FIELDS.map((f) => ({
    label: f.label,
    color: f.color,
    value: detail[f.key] ?? 0,
  }));
  const hasData = data.some((d) => d.value > 0);

  return (
    <Card>
      <CardHeader
        title={
          <div>
            <p className="text-sm font-semibold">Services & commerces</p>
            <p className="text-xs text-muted">
              {detail.niveau_equipement ?? "Nombre d'équipements"}
            </p>
          </div>
        }
      />

      {!hasData ? (
        <div className="grid h-[180px] place-items-center text-sm text-muted">
          Donnée indisponible
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={180}>
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 4, right: 36, bottom: 4, left: 8 }}
          >
            <XAxis type="number" hide />
            <YAxis
              type="category"
              dataKey="label"
              tickLine={false}
              axisLine={false}
              width={92}
              tick={{ fill: "#8a8f9c", fontSize: 12 }}
            />
            <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={16}>
              {data.map((d) => (
                <Cell key={d.label} fill={d.color} />
              ))}
              <LabelList
                dataKey="value"
                position="right"
                formatter={(v) => Number(v).toLocaleString("fr-FR")}
                style={{ fill: "#5b6172", fontSize: 11, fontWeight: 600 }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
}
