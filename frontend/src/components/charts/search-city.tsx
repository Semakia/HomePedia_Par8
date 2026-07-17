"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { api, type CityMetrics } from "@/lib/api";
import { formatPrixM2 } from "@/lib/mock";

/**
 * City picker that drives the stats page via `?ville=<code_commune>`. Searches
 * the API live (debounced) so *every* commune is reachable — not just the
 * preloaded page. Falls back to filtering `cities` client-side when the live
 * call fails (mock mode / API unreachable).
 */
export function SearchCity({
  cities,
  current,
  basePath = "/statistiques",
}: {
  cities: CityMetrics[];
  current: string;
  /** Route the picker navigates to (keeps the `?ville=` param). */
  basePath?: string;
}) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [matches, setMatches] = useState<CityMetrics[]>([]);
  const blurTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const currentName =
    cities.find((c) => c.code_commune === current)?.nom_commune ?? current;

  // Local filter over the preloaded list — used as the offline fallback.
  function localMatches(q: string) {
    return cities
      .filter((c) => c.nom_commune.toLowerCase().includes(q))
      .slice(0, 8);
  }

  useEffect(() => {
    const q = query.trim().toLowerCase();
    let cancelled = false;
    const timer = setTimeout(async () => {
      if (!q) {
        setMatches([]);
        return;
      }
      try {
        const { items } = await api.listCities({ q, size: 8 });
        if (!cancelled) setMatches(items.length > 0 ? items : localMatches(q));
      } catch {
        if (!cancelled) setMatches(localMatches(q));
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
    // `cities` is stable for the page; only re-run as the query changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  function select(code: string) {
    setQuery("");
    setOpen(false);
    router.push(`${basePath}?ville=${code}`);
  }

  return (
    <div className="relative w-full max-w-sm">
      <Search
        size={16}
        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
      />
      <input
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => {
          // Delay so a click on a result registers before the list unmounts.
          blurTimer.current = setTimeout(() => setOpen(false), 120);
        }}
        placeholder={`Rechercher une ville (actuel : ${currentName})`}
        className="w-full rounded-xl border border-line bg-card px-3 py-2.5 pl-9 text-sm outline-none focus:border-primary/40"
      />

      {open && matches.length > 0 && (
        <ul className="absolute z-20 mt-1 max-h-72 w-full overflow-y-auto rounded-xl border border-line bg-card p-1 shadow-lg">
          {matches.map((c) => (
            <li key={c.code_commune}>
              <button
                type="button"
                // onMouseDown fires before input blur, so the selection lands.
                onMouseDown={(e) => {
                  e.preventDefault();
                  if (blurTimer.current) clearTimeout(blurTimer.current);
                  select(c.code_commune);
                }}
                className="flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2 text-left text-sm hover:bg-bg"
              >
                <span className="min-w-0 flex-1 truncate font-medium">
                  {c.nom_commune}
                </span>
                <span className="shrink-0 text-xs text-muted">
                  {c.code_departement} · {formatPrixM2(c.prix_m2_median)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
