"use client";

import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";
import { Card, CardHeader } from "@/components/ui/card";
import type { CityDetail } from "@/lib/api";
import {
  DEFAULT_CRITERIA,
  DEFAULT_WEIGHTS,
  scoreCity,
  scoreColor,
} from "@/lib/scoring";

const AXES: { key: "budget" | "transport" | "services" | "jeune"; label: string }[] = [
  { key: "budget", label: "Budget" },
  { key: "transport", label: "Transport" },
  { key: "services", label: "Services" },
  { key: "jeune", label: "Jeunes actifs" },
];

/**
 * Match radar — the four matching sub-scores (budget / transport / services /
 * young-active fit) for this city, using the engine's default criteria/weights.
 * Ties the stats page back to the product's core scoring.
 */
export function MatchRadarCard({ detail }: { detail: CityDetail }) {
  const match = scoreCity(detail, DEFAULT_CRITERIA, DEFAULT_WEIGHTS);
  const color = scoreColor(match.score);
  const data = AXES.map((a) => ({
    axis: a.label,
    value: Math.round((match.sub[a.key] ?? 0) * 100),
  }));

  return (
    <Card>
      <CardHeader
        title={
          <div>
            <p className="text-sm font-semibold">Correspondance</p>
            <p className="text-xs text-muted">
              Profil de la ville selon nos critères
            </p>
          </div>
        }
        action={
          <span
            className="grid h-11 w-11 shrink-0 place-items-center rounded-full text-sm font-bold text-white"
            style={{ backgroundColor: color }}
            title="Score global"
          >
            {match.score}
          </span>
        }
      />

      <ResponsiveContainer width="100%" height={220}>
        <RadarChart data={data} outerRadius="72%">
          <PolarGrid stroke="#eceef3" />
          <PolarAngleAxis
            dataKey="axis"
            tick={{ fill: "#5b6172", fontSize: 12 }}
          />
          <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
          <Radar
            dataKey="value"
            stroke={color}
            fill={color}
            fillOpacity={0.35}
          />
        </RadarChart>
      </ResponsiveContainer>
    </Card>
  );
}
