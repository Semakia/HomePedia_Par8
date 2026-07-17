"use client";

import { useEffect, useState } from "react";
import {
  BarChart3,
  Building2,
  GraduationCap,
  Heart,
  Layers,
  ShoppingCart,
  Train,
  Users,
  X,
} from "lucide-react";
import { Line, LineChart, ResponsiveContainer, YAxis } from "recharts";
import {
  api,
  type CityDetail,
  type HousingPriceByType,
} from "@/lib/api";
import { formatPrixM2 } from "@/lib/mock";
import {
  DRILLABLE_COMMUNES,
  scoreColor,
  type ScoredCity,
} from "@/lib/scoring";

const SUB_LABELS: { key: "budget" | "transport" | "services" | "jeune"; label: string }[] = [
  { key: "budget", label: "Budget" },
  { key: "transport", label: "Transport" },
  { key: "services", label: "Services" },
  { key: "jeune", label: "Jeunes" },
];

export function CommuneFiche({
  city,
  onClose,
  onDrill,
  onViewStats,
}: {
  city: ScoredCity;
  onClose: () => void;
  onDrill?: (parentCode: string, departement: string) => void;
  onViewStats?: (codeCommune: string) => void;
}) {
  const [detail, setDetail] = useState<CityDetail | null>(null);
  const [housing, setHousing] = useState<HousingPriceByType[]>([]);

  // Lazily enrich with the monthly trend + dwelling-type split (extra calls
  // the list view doesn't need). Best-effort: the fiche is useful without them.
  // The parent keys this component on the commune, so state starts fresh on
  // each selection — no manual reset needed here.
  useEffect(() => {
    let alive = true;
    Promise.allSettled([
      api.getCity(city.code_commune),
      api.listHousingPrices({ code_commune: city.code_commune }),
    ]).then(([d, h]) => {
      if (!alive) return;
      if (d.status === "fulfilled") setDetail(d.value);
      if (h.status === "fulfilled") setHousing(h.value.items);
    });
    return () => {
      alive = false;
    };
  }, [city.code_commune]);

  const m = city.match;
  const drillDept = DRILLABLE_COMMUNES[city.code_commune];
  const trendData = (detail?.trend ?? [])
    .filter((p) => p.prix_m2_median != null)
    .map((p) => ({ x: `${p.year}-${p.month}`, v: p.prix_m2_median as number }));

  return (
    <div className="flex flex-col gap-4" data-tour="fiche">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted">
            {city.region ?? "—"} · dépt {city.code_departement}
          </p>
          <h2 className="text-lg font-semibold">{city.nom_commune}</h2>
          {city.type_commune && (
            <span className="mt-1 inline-flex items-center gap-1 rounded-full bg-primary-soft px-2 py-0.5 text-xs font-medium text-primary">
              <Building2 size={12} /> {city.type_commune}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg p-1 text-muted hover:bg-bg"
          aria-label="Fermer"
        >
          <X size={18} />
        </button>
      </div>

      {/* Score + breakdown */}
      <div className="flex items-center gap-4 rounded-2xl border border-line p-4">
        <div
          className="grid h-16 w-16 shrink-0 place-items-center rounded-full text-xl font-bold text-white"
          style={{ backgroundColor: scoreColor(m.score) }}
        >
          {m.score}
        </div>
        <div className="flex-1">
          <p className="mb-1 text-xs font-medium text-muted">Score de correspondance</p>
          <div className="flex flex-col gap-1.5">
            {SUB_LABELS.map(({ key, label }) => (
              <SubBar key={key} label={label} value={m.sub[key]} />
            ))}
          </div>
        </div>
      </div>

      {m.surfaceAtteignable != null && (
        <p className="rounded-xl bg-primary-soft px-3 py-2.5 text-sm text-primary">
          Avec votre budget, vous pourriez acheter ≈{" "}
          <b>{m.surfaceAtteignable} m²</b> ici.
        </p>
      )}

      {/* Headline stats */}
      <div className="grid grid-cols-2 gap-3">
        <Stat label="Prix médian" value={formatPrixM2(city.prix_m2_median)} />
        <Stat
          label="Abordabilité"
          value={city.affordability_class ?? "—"}
          sub={city.affordability_years != null ? `${city.affordability_years} ans de revenu` : undefined}
        />
        <Stat
          label="Revenu médian"
          value={city.revenu_median != null ? `${Math.round(city.revenu_median).toLocaleString("fr-FR")} €` : "—"}
        />
        <Stat
          label="Population"
          value={city.population != null ? city.population.toLocaleString("fr-FR") : "—"}
        />
      </div>

      {/* Monthly trend (lazy) */}
      {trendData.length > 1 && (
        <Section title="Évolution du prix médian">
          <ResponsiveContainer width="100%" height={70}>
            <LineChart data={trendData}>
              <YAxis hide domain={["dataMin", "dataMax"]} />
              <Line
                type="monotone"
                dataKey="v"
                stroke="#5d5fef"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </Section>
      )}

      {/* Dwelling-type split (lazy) */}
      {housing.length > 0 && (
        <Section title="Par type de bien">
          <div className="flex flex-col gap-2">
            {housing.map((h) => (
              <div key={h.type_local} className="flex items-center justify-between text-sm">
                <span className="text-muted">{h.type_local}</span>
                <span className="font-medium">{formatPrixM2(h.prix_m2_median)}</span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Transport */}
      <Section title="Transport">
        <div className="flex items-center gap-2 text-sm">
          <Train size={16} className="text-primary" />
          <span className="font-medium">{city.desserte_class ?? "—"}</span>
        </div>
        <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-muted">
          <span>{city.nb_gares ?? 0} gare(s)</span>
          {city.distance_gare_km != null && (
            <span>Gare à {city.distance_gare_km} km</span>
          )}
        </div>
      </Section>

      {/* Amenities */}
      <Section title="Services & commerces">
        <div className="mb-2 flex items-center gap-2 text-sm">
          <Layers size={16} className="text-primary" />
          <span className="font-medium">{city.niveau_equipement ?? "—"}</span>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <Amenity icon={Heart} label="Santé" value={city.nb_sante} />
          <Amenity icon={ShoppingCart} label="Commerces" value={city.nb_commerces} />
          <Amenity icon={GraduationCap} label="Enseignement" value={city.nb_enseignement} />
          <Amenity icon={Building2} label="Supermarchés" value={city.nb_supermarche} />
        </div>
      </Section>

      {/* Demographics */}
      <Section title="Profil de population">
        <div className="mb-2 flex items-center gap-2 text-xs text-muted">
          <Users size={14} /> Répartition par âge
        </div>
        <AgeBar
          moins25={city.pct_moins25}
          actifs={city.pct_25_64}
          seniors={city.pct_65plus}
        />
      </Section>

      <div className="mt-1 flex flex-col gap-2">
        {drillDept && onDrill && (
          <button
            type="button"
            onClick={() => onDrill(city.code_commune, drillDept)}
            className="rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-white hover:bg-primary/90"
          >
            Explorer les arrondissements →
          </button>
        )}
        {onViewStats && (
          <button
            type="button"
            data-tour="view-stats"
            onClick={() => onViewStats(city.code_commune)}
            className="flex items-center justify-center gap-1.5 rounded-xl border border-primary/40 px-4 py-2.5 text-sm font-medium text-primary hover:bg-primary-soft"
          >
            <BarChart3 size={15} /> Voir les statistiques →
          </button>
        )}
      </div>
    </div>
  );
}

function SubBar({ label, value }: { label: string; value: number | null }) {
  const pct = value == null ? 0 : Math.round(value * 100);
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-16 shrink-0 text-muted">{label}</span>
      <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-line">
        <span
          className="block h-full rounded-full bg-primary"
          style={{ width: `${pct}%`, opacity: value == null ? 0.2 : 1 }}
        />
      </span>
      <span className="w-8 shrink-0 text-right tabular-nums text-muted">
        {value == null ? "—" : pct}
      </span>
    </div>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-line p-3">
      <p className="text-xs text-muted">{label}</p>
      <p className="text-sm font-semibold">{value}</p>
      {sub && <p className="text-[11px] text-muted">{sub}</p>}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
        {title}
      </h3>
      {children}
    </div>
  );
}

function Amenity({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Heart;
  label: string;
  value: number | null | undefined;
}) {
  return (
    <div className="flex items-center gap-2 rounded-lg bg-bg px-2.5 py-2 text-xs">
      <Icon size={14} className="shrink-0 text-muted" />
      <span className="flex-1 text-muted">{label}</span>
      <span className="font-semibold tabular-nums">
        {value != null ? value.toLocaleString("fr-FR") : "—"}
      </span>
    </div>
  );
}

function AgeBar({
  moins25,
  actifs,
  seniors,
}: {
  moins25: number | null | undefined;
  actifs: number | null | undefined;
  seniors: number | null | undefined;
}) {
  if (moins25 == null && actifs == null && seniors == null) {
    return <p className="text-xs text-muted">Donnée indisponible</p>;
  }
  const seg = [
    { v: moins25 ?? 0, color: "#5d5fef", label: "−25 ans" },
    { v: actifs ?? 0, color: "#22c55e", label: "25–64" },
    { v: seniors ?? 0, color: "#f59e0b", label: "65+" },
  ];
  return (
    <div>
      <div className="flex h-3 overflow-hidden rounded-full">
        {seg.map((s) => (
          <span key={s.label} style={{ width: `${s.v}%`, backgroundColor: s.color }} />
        ))}
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted">
        {seg.map((s) => (
          <span key={s.label} className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: s.color }} />
            {s.label} {s.v.toFixed(0)}%
          </span>
        ))}
      </div>
    </div>
  );
}
