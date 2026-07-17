"use client";

import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, Download, Search } from "lucide-react";
import type { ArrondissementMetrics } from "@/lib/api";
import { AFFORDABILITY_COLOR } from "@/lib/scoring";

// Parent communes that have arrondissement-level Gold data.
const DEPARTEMENTS: { code: string; label: string }[] = [
  { code: "all", label: "Toutes" },
  { code: "75", label: "Paris" },
  { code: "69", label: "Lyon" },
  { code: "13", label: "Marseille" },
];

// Order used when sorting on the (textual) affordability class.
const AFFORDABILITY_RANK: Record<string, number> = {
  "Très abordable": 0,
  Abordable: 1,
  Tendu: 2,
  "Très tendu": 3,
};

type Row = ArrondissementMetrics;
type Align = "left" | "right";

type Column = {
  key: string;
  label: string;
  align: Align;
  /** Numeric/string value used for sorting; null sinks to the bottom. */
  sortValue: (r: Row) => number | string | null;
  render: (r: Row) => React.ReactNode;
};

const nf = new Intl.NumberFormat("fr-FR");
const fmtInt = (v: number | null | undefined) => (v == null ? "—" : nf.format(Math.round(v)));
const fmtEur = (v: number | null | undefined) => (v == null ? "—" : `${nf.format(Math.round(v))} €`);
const fmtDec = (v: number | null | undefined) => (v == null ? "—" : nf.format(v));

// "Paris 16e Arrondissement" → "Paris 16e" (the redundant word wastes column width).
const shortName = (r: Row) => r.nom_arrondissement.replace(/\s*Arrondissement$/i, "");

const COLUMNS: Column[] = [
  {
    key: "nom",
    label: "Arrondissement",
    align: "left",
    sortValue: (r) => shortName(r),
    render: (r) => (
      <span className="font-medium text-ink">
        {shortName(r)}
        <span className="ml-2 text-xs font-normal text-muted">{r.code_arrondissement}</span>
      </span>
    ),
  },
  {
    key: "prix_m2_median",
    label: "Prix médian €/m²",
    align: "right",
    sortValue: (r) => r.prix_m2_median ?? null,
    render: (r) => fmtEur(r.prix_m2_median),
  },
  {
    key: "surface_median",
    label: "Surface méd.",
    align: "right",
    sortValue: (r) => r.surface_median ?? null,
    render: (r) => (r.surface_median == null ? "—" : `${fmtDec(r.surface_median)} m²`),
  },
  {
    key: "revenu_median",
    label: "Revenu médian",
    align: "right",
    sortValue: (r) => r.revenu_median ?? null,
    render: (r) => fmtEur(r.revenu_median),
  },
  {
    key: "population",
    label: "Population",
    align: "right",
    sortValue: (r) => r.population ?? null,
    render: (r) => fmtInt(r.population),
  },
  {
    key: "nb_transactions",
    label: "Transactions",
    align: "right",
    sortValue: (r) => r.nb_transactions ?? null,
    render: (r) => fmtInt(r.nb_transactions),
  },
  {
    key: "affordability_years",
    label: "Années de revenu",
    align: "right",
    sortValue: (r) => r.affordability_years ?? null,
    render: (r) => (r.affordability_years == null ? "—" : `${fmtDec(r.affordability_years)} ans`),
  },
  {
    key: "m2_par_an",
    label: "m² / an",
    align: "right",
    sortValue: (r) => r.m2_par_an ?? null,
    render: (r) => fmtDec(r.m2_par_an),
  },
  {
    key: "affordability_class",
    label: "Abordabilité",
    align: "left",
    sortValue: (r) =>
      r.affordability_class == null ? null : AFFORDABILITY_RANK[r.affordability_class] ?? 99,
    render: (r) =>
      r.affordability_class == null ? (
        "—"
      ) : (
        <span
          className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium"
          style={{
            backgroundColor: `${AFFORDABILITY_COLOR[r.affordability_class] ?? "#94a3b8"}1a`,
            color: AFFORDABILITY_COLOR[r.affordability_class] ?? "#475569",
          }}
        >
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{ backgroundColor: AFFORDABILITY_COLOR[r.affordability_class] ?? "#94a3b8" }}
          />
          {r.affordability_class}
        </span>
      ),
  },
];

function compare(a: number | string | null, b: number | string | null, order: "asc" | "desc") {
  // Nulls always sink, regardless of sort direction.
  if (a == null && b == null) return 0;
  if (a == null) return 1;
  if (b == null) return -1;
  const cmp = typeof a === "number" && typeof b === "number" ? a - b : String(a).localeCompare(String(b), "fr");
  return order === "asc" ? cmp : -cmp;
}

function toCsv(rows: Row[]): string {
  const header = COLUMNS.map((c) => c.label);
  const lines = rows.map((r) =>
    COLUMNS.map((c) => {
      const v = c.sortValue(r);
      const cell = v == null ? "" : String(v);
      // Quote cells containing separators/quotes.
      return /[",;\n]/.test(cell) ? `"${cell.replace(/"/g, '""')}"` : cell;
    }).join(";"),
  );
  return [header.join(";"), ...lines].join("\n");
}

export function ArrondissementsTable({ rows }: { rows: Row[] }) {
  const [dept, setDept] = useState("75");
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState("prix_m2_median");
  const [order, setOrder] = useState<"asc" | "desc">("desc");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const col = COLUMNS.find((c) => c.key === sortKey) ?? COLUMNS[1];
    return rows
      .filter((r) => (dept === "all" ? true : r.code_departement === dept))
      .filter((r) => (q === "" ? true : shortName(r).toLowerCase().includes(q)))
      .sort((a, b) => compare(col.sortValue(a), col.sortValue(b), order));
  }, [rows, dept, query, sortKey, order]);

  const onSort = (key: string) => {
    if (key === sortKey) {
      setOrder((o) => (o === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      // Names read best A→Z; numbers most-interesting high→low.
      setOrder(key === "nom" || key === "affordability_class" ? "asc" : "desc");
    }
  };

  const downloadCsv = () => {
    const blob = new Blob(["﻿" + toCsv(filtered)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `arrondissements-${dept}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="inline-flex rounded-xl border border-line bg-card p-1">
          {DEPARTEMENTS.map((d) => (
            <button
              key={d.code}
              type="button"
              onClick={() => setDept(d.code)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                dept === d.code ? "bg-primary text-white" : "text-muted hover:text-ink"
              }`}
            >
              {d.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <Search
              size={15}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
            />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Rechercher…"
              className="w-48 rounded-xl border border-line bg-card py-2 pl-9 pr-3 text-sm outline-none focus:border-primary/50"
            />
          </div>
          <button
            type="button"
            onClick={downloadCsv}
            className="inline-flex items-center gap-2 rounded-xl border border-line px-3 py-2 text-sm font-medium text-primary hover:bg-primary-soft"
          >
            <Download size={15} />
            CSV
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-2xl border border-line bg-card">
        <table className="w-full min-w-[880px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-line">
              <th className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted/70">
                #
              </th>
              {COLUMNS.map((col) => {
                const active = col.key === sortKey;
                const Icon = active ? (order === "asc" ? ArrowUp : ArrowDown) : ArrowUpDown;
                return (
                  <th
                    key={col.key}
                    aria-sort={active ? (order === "asc" ? "ascending" : "descending") : "none"}
                    className={`px-3 py-3 text-xs font-semibold uppercase tracking-wider ${
                      col.align === "right" ? "text-right" : "text-left"
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => onSort(col.key)}
                      className={`inline-flex items-center gap-1.5 transition-colors hover:text-ink ${
                        col.align === "right" ? "flex-row-reverse" : ""
                      } ${active ? "text-primary" : "text-muted/70"}`}
                    >
                      {col.label}
                      <Icon size={13} className={active ? "opacity-100" : "opacity-40"} />
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={COLUMNS.length + 1} className="px-3 py-10 text-center text-muted">
                  Aucun arrondissement ne correspond à votre recherche.
                </td>
              </tr>
            ) : (
              filtered.map((r, i) => (
                <tr key={r.code_arrondissement} className="border-b border-line/60 last:border-0 hover:bg-bg">
                  <td className="px-3 py-3 text-center text-sm font-semibold text-muted">{i + 1}</td>
                  {COLUMNS.map((col) => (
                    <td
                      key={col.key}
                      className={`px-3 py-3 tabular-nums ${
                        col.align === "right" ? "text-right" : "text-left"
                      }`}
                    >
                      {col.render(r)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-muted">
        {filtered.length} arrondissement{filtered.length > 1 ? "s" : ""} · source&nbsp;:
        <span className="font-medium"> market.arrondissement_metrics</span> (couche Gold)
      </p>
    </div>
  );
}
