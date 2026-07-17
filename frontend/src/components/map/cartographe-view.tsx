"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, Train } from "lucide-react";
import type { FeatureCollection } from "geojson";
import { Card } from "@/components/ui/card";
import {
  api,
  type ArrondissementMetrics,
  type CityMetrics,
  type Gare,
} from "@/lib/api";
import {
  FRANCE_BOUNDS,
  IDF_BOUNDS,
  IDF_DEPARTEMENTS,
  fetchContours,
  fetchDepartementContours,
} from "@/lib/geo";
import { formatPrixM2 } from "@/lib/mock";
import {
  COLOR_MODES,
  colorForCity,
  legendForMode,
  type ColorMode,
} from "@/lib/map-modes";
import {
  AFFORDABILITY_COLOR,
  DEFAULT_CRITERIA,
  DEFAULT_WEIGHTS,
  aggregateByDepartement,
  rankCities,
  type Criteria,
  type Weights,
} from "@/lib/scoring";
import { usePreferences } from "@/components/preferences-provider";
import { notify } from "@/components/onboarding/onboarding-provider";
import { CartographeMap } from "./cartographe-map";
import { CommuneFiche } from "./commune-fiche";
import { CriteriaPanel } from "./criteria-panel";
import type { MapPoint } from "./france-map";
import { RecommendationList } from "./recommendation-list";

type Drill = {
  parentCode: string;
  parentName: string;
  departement: string;
  items: ArrondissementMetrics[];
};

// Working criteria/weights persist across client-side navigation (e.g. opening
// /statistiques and coming back) via this module-level session cache. It is
// only mutated from client event handlers, so it never leaks across SSR
// requests; a full page reload resets it to the defaults.
let sessionCriteria: Criteria | null = null;
let sessionWeights: Weights | null = null;

export function CartographeView({
  cities,
  gares,
  scope,
}: {
  cities: CityMetrics[];
  gares: Gare[];
  scope: "idf" | "france";
}) {
  const router = useRouter();
  const { prefs } = usePreferences();
  const [criteria, setCriteriaState] = useState<Criteria>(
    sessionCriteria ?? DEFAULT_CRITERIA,
  );
  const [weights, setWeightsState] = useState<Weights>(
    sessionWeights ?? DEFAULT_WEIGHTS,
  );
  // Mirror updates into the session cache so they survive navigation.
  const setCriteria = useCallback((next: Criteria) => {
    sessionCriteria = next;
    setCriteriaState(next);
  }, []);
  const setWeights = useCallback((next: Weights) => {
    sessionWeights = next;
    setWeightsState(next);
  }, []);
  const [colorMode, setColorMode] = useState<ColorMode>(prefs.mapColorMode);
  const [showGares, setShowGares] = useState(prefs.mapShowGares);

  // Adopt the user's default map preferences (from /parametres). Adjusting state
  // during render (rather than in an effect) keeps SSR/hydration consistent: the
  // first client render still matches the server, then re-renders once the
  // stored prefs resolve. Re-applies if the defaults change in Settings.
  const [defaultMode, setDefaultMode] = useState(prefs.mapColorMode);
  if (prefs.mapColorMode !== defaultMode) {
    setDefaultMode(prefs.mapColorMode);
    setColorMode(prefs.mapColorMode);
  }
  const [defaultGares, setDefaultGares] = useState(prefs.mapShowGares);
  if (prefs.mapShowGares !== defaultGares) {
    setDefaultGares(prefs.mapShowGares);
    setShowGares(prefs.mapShowGares);
  }
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  // Selecting a commune (from the list or the map) — also drives the tour.
  const handleSelectCommune = useCallback((id: string | null) => {
    setSelectedCode(id);
    if (id) notify("recommendations");
  }, []);
  const [drill, setDrill] = useState<Drill | null>(null);
  const [selectedArr, setSelectedArr] = useState<string | null>(null);
  // France scope: the department drilled into (null = the overview choropleth).
  const [deptView, setDeptView] = useState<{ code: string; nom: string } | null>(
    null,
  );
  // Commune contours tagged with the department-set they were fetched for, so a
  // stale set (mid-switch) is ignored at render rather than briefly drawn.
  const [contours, setContours] = useState<{
    key: string;
    fc: FeatureCollection;
  } | null>(null);
  const [deptGeo, setDeptGeo] = useState<FeatureCollection | null>(null);

  // Three render modes:
  //  - arrondissement drill: point markers (opened from a commune fiche);
  //  - France overview: a department choropleth (~96 polygons);
  //  - commune choropleth: Île-de-France, or the communes of a drilled department.
  const inArrDrill = drill !== null;
  const inDeptChoropleth = scope === "france" && !deptView && !inArrDrill;
  const inCommuneChoropleth =
    !inArrDrill && (scope === "idf" || (scope === "france" && deptView !== null));

  // Which departments' communes the choropleth should show right now.
  const communeDepts = !inCommuneChoropleth
    ? []
    : scope === "idf"
      ? IDF_DEPARTEMENTS
      : deptView
        ? [deptView.code]
        : [];
  const communeKey = communeDepts.join(",");

  // Reset a drilled department when the scope flips. Adjusting state during
  // render is React's recommended alternative to a setState-in-effect.
  const [prevScope, setPrevScope] = useState(scope);
  if (scope !== prevScope) {
    setPrevScope(scope);
    setDeptView(null);
  }

  // Department polygons for the France overview (bundled, fetched once).
  useEffect(() => {
    if (!inDeptChoropleth) return;
    let alive = true;
    fetchDepartementContours()
      .then((fc) => alive && setDeptGeo(fc))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [inDeptChoropleth]);

  // Commune polygons for the active commune choropleth (IDF, or a drilled dept).
  useEffect(() => {
    if (!communeKey) return;
    let alive = true;
    fetchContours(communeKey.split(","))
      .then((fc) => alive && setContours({ key: communeKey, fc }))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [communeKey]);

  // Only use the contours if they match the set we currently want (else null —
  // no stale polygons flash while the new department's communes load).
  const communeGeo = contours?.key === communeKey ? contours.fc : null;

  // Score + rank once per criteria/weights change.
  const ranked = useMemo(
    () => rankCities(cities, criteria, weights),
    [cities, criteria, weights],
  );
  // Code -> scored commune lookup for the choropleth's per-feature styling.
  const cityByCode = useMemo(
    () => new Map(ranked.map((c) => [c.code_commune, c])),
    [ranked],
  );
  const selectedCity = useMemo(
    () => ranked.find((c) => c.code_commune === selectedCode) ?? null,
    [ranked, selectedCode],
  );
  const matchCount = useMemo(
    () => ranked.filter((c) => c.match.passesFilters).length,
    [ranked],
  );

  // France overview: one synthetic scored row per department for the choropleth.
  const deptByCode = useMemo(
    () => (scope === "france" ? aggregateByDepartement(ranked) : new Map()),
    [scope, ranked],
  );
  // Communes feeding the active commune choropleth (all of IDF, or one dept).
  const communesInView = useMemo(() => {
    if (scope === "france" && deptView) {
      return ranked.filter((c) => c.code_departement === deptView.code);
    }
    return ranked;
  }, [scope, deptView, ranked]);

  // Map points: arrondissement markers when drilling; otherwise the communes of
  // the active choropleth (used only for framing/fly-to, not drawn as markers).
  // The department overview needs no points (it frames on FRANCE_BOUNDS).
  const points: MapPoint[] = useMemo(() => {
    if (drill) {
      return drill.items
        .filter((a) => a.latitude != null && a.longitude != null)
        .map((a) => ({
          id: a.code_arrondissement,
          lat: a.latitude!,
          lng: a.longitude!,
          color: a.affordability_class
            ? AFFORDABILITY_COLOR[a.affordability_class] ?? "#cbd5e1"
            : "#cbd5e1",
          label: a.nom_arrondissement,
          sub: formatPrixM2(a.prix_m2_median),
        }));
    }
    if (inDeptChoropleth) return [];
    return communesInView
      .filter((c) => c.latitude != null && c.longitude != null)
      .map((c) => ({
        id: c.code_commune,
        lat: c.latitude!,
        lng: c.longitude!,
        color: colorForCity(colorMode, c),
        label: c.nom_commune,
        sub: `${formatPrixM2(c.prix_m2_median)} · score ${c.match.score}`,
        muted: !c.match.passesFilters,
      }));
  }, [drill, inDeptChoropleth, communesInView, colorMode]);

  // Enter a department's commune view from the overview choropleth.
  const enterDept = useCallback(
    (code: string) => {
      const feat = deptGeo?.features.find((f) => f.properties?.code === code);
      const nom = (feat?.properties?.nom as string | undefined) ?? code;
      setDeptView({ code, nom });
      setSelectedCode(null);
    },
    [deptGeo],
  );

  async function openDrill(parentCode: string, departement: string) {
    const parentName =
      cities.find((c) => c.code_commune === parentCode)?.nom_commune ?? "";
    try {
      const { items } = await api.listArrondissements({
        code_commune_parent: parentCode,
        size: 200,
      });
      setDrill({ parentCode, parentName, departement, items });
      setSelectedArr(null);
      setSelectedCode(null);
    } catch {
      // Drill-down unavailable — stay on the commune view.
    }
  }

  const selectedArrData = drill?.items.find(
    (a) => a.code_arrondissement === selectedArr,
  );

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Cartographe</h1>
          <p className="text-sm text-muted">
            {drill
              ? `Arrondissements de ${drill.parentName}`
              : deptView
                ? `Communes de ${deptView.nom}`
                : inDeptChoropleth
                  ? "Vue par département — cliquez un département pour explorer ses communes"
                  : `${matchCount} commune${matchCount > 1 ? "s" : ""} correspondent à vos critères`}
          </p>
        </div>
        <ScopeToggle
          scope={scope}
          disabled={Boolean(drill) || Boolean(deptView)}
          onChange={(s) => router.push(s === "idf" ? "/?scope=idf" : "/")}
        />
      </div>

      {/* items-start: each column keeps its natural height (no stretching to
          the tallest), so the fiche is never clipped. The map column sticks so
          it stays in view while the (possibly tall) fiche is read. */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[300px_1fr_320px] lg:items-start">
        {/* Left — criteria */}
        <Card className="order-2 lg:sticky lg:top-4 lg:order-1 lg:max-h-[calc(100vh-2rem)] lg:overflow-y-auto">
          <CriteriaPanel
            criteria={criteria}
            weights={weights}
            onCriteria={setCriteria}
            onWeights={setWeights}
            onReset={() => {
              setCriteria(DEFAULT_CRITERIA);
              setWeights(DEFAULT_WEIGHTS);
            }}
          />
        </Card>

        {/* Center — map (sticky so it stays visible while reading the fiche) */}
        <div className="order-1 flex flex-col gap-3 lg:sticky lg:top-4 lg:order-2">
          {(drill || deptView) && (
            <button
              type="button"
              onClick={() => {
                if (drill) {
                  setDrill(null);
                  setSelectedArr(null);
                } else {
                  setDeptView(null);
                  setSelectedCode(null);
                }
              }}
              className="flex w-fit items-center gap-1 rounded-lg border border-line bg-card px-3 py-1.5 text-sm hover:bg-bg"
            >
              <ChevronLeft size={15} />{" "}
              {drill ? "Retour aux communes" : "Retour à la France"}
            </button>
          )}
          {!drill && (
            <div className="flex flex-wrap items-center gap-2">
              {COLOR_MODES.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => setColorMode(m.id)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                    colorMode === m.id
                      ? "bg-primary text-white"
                      : "border border-line bg-card text-muted hover:bg-bg"
                  }`}
                >
                  {m.label}
                </button>
              ))}
              <button
                type="button"
                onClick={() => setShowGares((v) => !v)}
                className={`ml-auto flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                  showGares
                    ? "bg-ink text-bg"
                    : "border border-line bg-card text-muted hover:bg-bg"
                }`}
              >
                <Train size={14} /> Gares
              </button>
            </div>
          )}

          <Card className="relative p-0">
            <div className="relative h-[600px] overflow-hidden rounded-2xl">
              <CartographeMap
                points={points}
                fitKey={
                  drill
                    ? `arr-${drill.parentCode}`
                    : inDeptChoropleth
                      ? "france-depts"
                      : `communes-${scope}-${deptView?.code ?? "idf"}`
                }
                frameBounds={
                  inDeptChoropleth
                    ? FRANCE_BOUNDS
                    : scope === "idf" && !drill
                      ? IDF_BOUNDS
                      : undefined // arr drill / drilled dept: fit to the points
                }
                geojson={
                  inDeptChoropleth
                    ? deptGeo
                    : inCommuneChoropleth
                      ? communeGeo
                      : null
                }
                cityByCode={inDeptChoropleth ? deptByCode : cityByCode}
                colorMode={colorMode}
                gares={gares}
                showGares={showGares && inCommuneChoropleth}
                selectedId={drill ? selectedArr : selectedCode}
                onSelect={(id) => {
                  if (drill) setSelectedArr(id);
                  else if (inDeptChoropleth) enterDept(id);
                  else handleSelectCommune(id);
                }}
              />
              <MapLegend mode={drill ? "abordabilite" : colorMode} />
            </div>
          </Card>
        </div>

        {/* Right — fiche / recommendations (natural height, top-aligned: the
            full fiche is always visible, the page scrolls if it's long) */}
        <Card className="order-3">
          {drill ? (
            selectedArrData ? (
              <ArrondissementPanel
                arr={selectedArrData}
                onClose={() => setSelectedArr(null)}
              />
            ) : (
              <p className="text-sm text-muted">
                Cliquez un arrondissement sur la carte pour voir le détail.
              </p>
            )
          ) : selectedCity ? (
            <CommuneFiche
              key={selectedCity.code_commune}
              city={selectedCity}
              onClose={() => setSelectedCode(null)}
              onDrill={openDrill}
              onViewStats={(code) => {
                notify("view-stats");
                router.push(`/statistiques?ville=${code}`);
              }}
            />
          ) : (
            <RecommendationList
              cities={ranked.filter((c) => c.match.passesFilters)}
              selectedId={selectedCode}
              onSelect={handleSelectCommune}
            />
          )}
        </Card>
      </div>
    </div>
  );
}

function ScopeToggle({
  scope,
  disabled,
  onChange,
}: {
  scope: "idf" | "france";
  disabled?: boolean;
  onChange: (scope: "idf" | "france") => void;
}) {
  return (
    <div className="flex rounded-xl border border-line bg-card p-0.5 text-sm">
      {(["idf", "france"] as const).map((s) => (
        <button
          key={s}
          type="button"
          disabled={disabled}
          onClick={() => onChange(s)}
          className={`rounded-lg px-3 py-1.5 transition-colors disabled:opacity-40 ${
            scope === s ? "bg-primary-soft font-medium text-primary" : "text-muted"
          }`}
        >
          {s === "idf" ? "Île-de-France" : "France"}
        </button>
      ))}
    </div>
  );
}

function MapLegend({ mode }: { mode: ColorMode }) {
  return (
    <div className="absolute bottom-3 left-3 z-[1000] rounded-xl bg-card/90 p-3 text-xs shadow-sm backdrop-blur">
      <div className="flex flex-col gap-1.5">
        {legendForMode(mode).map((item) => (
          <span key={item.label} className="flex items-center gap-2">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: item.color }}
            />
            {item.label}
          </span>
        ))}
      </div>
    </div>
  );
}

function ArrondissementPanel({
  arr,
  onClose,
}: {
  arr: ArrondissementMetrics;
  onClose: () => void;
}) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted">
            {arr.nom_commune_parent} · dépt {arr.code_departement}
          </p>
          <h2 className="text-lg font-semibold">{arr.nom_arrondissement}</h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-sm text-muted hover:text-ink"
        >
          Fermer
        </button>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Stat label="Prix médian" value={formatPrixM2(arr.prix_m2_median)} />
        <Stat
          label="Abordabilité"
          value={arr.affordability_class ?? "—"}
          sub={arr.affordability_years != null ? `${arr.affordability_years} ans de revenu` : undefined}
        />
        <Stat
          label="Revenu médian"
          value={arr.revenu_median != null ? `${Math.round(arr.revenu_median).toLocaleString("fr-FR")} €` : "—"}
        />
        <Stat
          label="Population"
          value={arr.population != null ? arr.population.toLocaleString("fr-FR") : "—"}
        />
        <Stat
          label="Surface médiane"
          value={arr.surface_median != null ? `${arr.surface_median} m²` : "—"}
        />
        <Stat label="Transactions" value={arr.nb_transactions.toLocaleString("fr-FR")} />
      </div>
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
