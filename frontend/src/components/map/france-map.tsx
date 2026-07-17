"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  CircleMarker,
  GeoJSON,
  MapContainer,
  Tooltip,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet";
import type { GeoJSON as LeafletGeoJSON, PathOptions } from "leaflet";
import { LatLngBounds } from "leaflet";
import type { FeatureCollection } from "geojson";
import "leaflet/dist/leaflet.css";
import type { Gare } from "@/lib/api";
import type { BBox } from "@/lib/geo";
import { colorForCity, type ColorMode } from "@/lib/map-modes";
import type { ScoredCity } from "@/lib/scoring";
import { useIsDark } from "@/components/preferences-provider";

// Basemaps: light = OSM standard, dark = CARTO dark (free, OSM-derived).
const TILES = {
  light: {
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  },
  dark: {
    // No-subdomain host: the legacy {s}=a/b/c.basemap.cartocdn.com hosts now
    // 503; basemaps.cartocdn.com is CARTO's current endpoint (HTTP/2, no sharding).
    url: "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
  },
} as const;

/** Generic marker the map renders — communes and arrondissements both map to it. */
export type MapPoint = {
  id: string;
  lat: number;
  lng: number;
  color: string;
  label: string;
  sub?: string;
  /** Dimmed when it fails the user's hard filters. */
  muted?: boolean;
};

// Metropolitan France bounding box (incl. Corsica). Used to frame the map
// without letting overseas communes (Réunion, Guyane, Mayotte…) blow the
// viewport out to a world view.
const METRO_FR = { latMin: 41, latMax: 51.5, lngMin: -5.5, lngMax: 9.8 };

// Frames the viewport on the current geographic set. `fitKey` identifies that
// set (scope / drill target): we refit only when it changes — NOT when markers
// merely recolor (mode/criteria changes), which would otherwise re-zoom the map
// on every interaction. When a fixed `box` is given (a scope's region) it frames
// that, so the view centers on the whole scope regardless of which communes have
// data; otherwise it falls back to the bounding box of the points themselves.
function FitBounds({
  points,
  fitKey,
  box,
}: {
  points: MapPoint[];
  fitKey: string;
  box?: BBox;
}) {
  const map = useMap();
  const lastFit = useRef<string>("");
  useEffect(() => {
    if (lastFit.current === fitKey) return;
    let bounds: LatLngBounds | null = null;
    if (box) {
      bounds = new LatLngBounds(box[0], box[1]);
    } else if (points.length > 0) {
      const onshore = points.filter(
        (p) =>
          p.lat >= METRO_FR.latMin &&
          p.lat <= METRO_FR.latMax &&
          p.lng >= METRO_FR.lngMin &&
          p.lng <= METRO_FR.lngMax,
      );
      const framed = onshore.length > 0 ? onshore : points;
      bounds = new LatLngBounds(framed.map((p) => [p.lat, p.lng]));
    }
    if (!bounds) return;
    lastFit.current = fitKey;
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 13 });
  }, [points, fitKey, box, map]);
  return null;
}

// Pans/zooms onto the selected marker for a close-up when the selection changes
// (map click or recommendation-list click). Points are read from a ref so a
// mere recolor (mode/criteria change) doesn't re-trigger a fly-to — only an
// actual selection change does.
function FlyToSelected({
  points,
  selectedId,
}: {
  points: MapPoint[];
  selectedId: string | null;
}) {
  const map = useMap();
  // Keep the latest points in a ref (updated in an effect, not during render)
  // so the fly-to below depends only on the selection.
  const pointsRef = useRef(points);
  useEffect(() => {
    pointsRef.current = points;
  }, [points]);
  useEffect(() => {
    if (!selectedId) return;
    const p = pointsRef.current.find((pt) => pt.id === selectedId);
    if (!p) return;
    // Zoom in for the close-up, but never zoom back out if the user is already
    // closer than the target level.
    map.flyTo([p.lat, p.lng], Math.max(map.getZoom(), 13), { duration: 0.6 });
  }, [selectedId, map]);
  return null;
}

const NO_DATA_STYLE: PathOptions = {
  fillColor: "#e5e7eb",
  fillOpacity: 0.25,
  color: "#ffffff",
  weight: 0.5,
};

// Commune choropleth: each boundary polygon is filled by the active metric,
// joined to the scored data by INSEE code. Re-styles imperatively when the
// color mode / scores / selection change (cheaper than re-creating the layer).
function ChoroplethLayer({
  geojson,
  cityByCode,
  mode,
  selectedId,
  onSelect,
}: {
  geojson: FeatureCollection;
  cityByCode: Map<string, ScoredCity>;
  mode: ColorMode;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const ref = useRef<LeafletGeoJSON>(null);

  const styleFor = useCallback(
    (code: string | undefined): PathOptions => {
      const c = code ? cityByCode.get(code) : undefined;
      if (!c) return NO_DATA_STYLE;
      const selected = code === selectedId;
      return {
        fillColor: colorForCity(mode, c),
        fillOpacity: c.match.passesFilters ? 0.78 : 0.12,
        color: selected ? "#1a1d2e" : "#ffffff",
        weight: selected ? 2.5 : 0.5,
      };
    },
    [cityByCode, mode, selectedId],
  );

  // Tooltip HTML for a feature. `onEachFeature` only runs once (at layer
  // creation), so we also rebuild the content imperatively below — otherwise a
  // criteria/mode change repaints the polygons but leaves a stale price/score.
  const tooltipFor = useCallback(
    (code: string | undefined, nom: string): string => {
      const c = code ? cityByCode.get(code) : undefined;
      const detail =
        c?.prix_m2_median != null
          ? `<br/>${c.prix_m2_median.toLocaleString("fr-FR")} €/m² · score ${c.match.score}`
          : "<br/>donnée indisponible";
      return `<b>${nom}</b>${detail}`;
    },
    [cityByCode],
  );

  // Latest style/tooltip fns in refs so feature event handlers (bound once at
  // creation) never restyle with a stale color mode.
  const styleRef = useRef(styleFor);
  const tooltipRef = useRef(tooltipFor);
  useEffect(() => {
    styleRef.current = styleFor;
    tooltipRef.current = tooltipFor;
  }, [styleFor, tooltipFor]);

  // Re-style + refresh tooltips when the scale / selection / scores change.
  useEffect(() => {
    const layer = ref.current;
    if (!layer) return;
    layer.eachLayer((l) => {
      const path = l as unknown as {
        feature?: { properties?: { code?: string; nom?: string } };
        setStyle: (s: PathOptions) => void;
        setTooltipContent: (html: string) => void;
        getTooltip: () => unknown;
        bringToFront: () => void;
      };
      const code = path.feature?.properties?.code;
      path.setStyle(styleFor(code));
      if (path.getTooltip()) {
        const nom =
          path.feature?.properties?.nom ??
          (code ? cityByCode.get(code)?.nom_commune : undefined) ??
          "";
        path.setTooltipContent(tooltipFor(code, nom));
      }
      if (code === selectedId) path.bringToFront();
    });
  }, [styleFor, tooltipFor, cityByCode, selectedId]);

  return (
    <GeoJSON
      ref={ref}
      data={geojson}
      style={(feature) => styleRef.current(feature?.properties?.code)}
      onEachFeature={(feature, layer) => {
        const code: string | undefined = feature.properties?.code;
        const c = code ? cityByCode.get(code) : undefined;
        const nom = feature.properties?.nom ?? c?.nom_commune ?? "";
        layer.bindTooltip(tooltipRef.current(code, nom), { sticky: true });
        layer.on({
          click: () => code && onSelect(code),
          mouseover: (e) => e.target.setStyle({ weight: 2, color: "#1a1d2e" }),
          mouseout: (e) => e.target.setStyle(styleRef.current(code)),
        });
      }}
    />
  );
}

// --- Point clustering (dependency-free, screen-grid) -----------------------
// France scope feeds ~32k communes; rendering one marker each would choke the
// browser. We bucket the *visible* points into a fixed screen-pixel grid and
// draw one bubble per cell (count-sized), plus singletons as normal markers.
// Recomputed on pan/zoom; clicking a cluster zooms in to break it apart.
const CLUSTER_THRESHOLD = 400; // below this (drill-down / IDF points) skip clustering
const CLUSTER_CELL_PX = 64; // grid cell size on screen

/** A single commune marker (also used as a cluster's singleton leaf). */
function LeafMarker({
  p,
  selected,
  onSelect,
}: {
  p: MapPoint;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <CircleMarker
      center={[p.lat, p.lng]}
      radius={selected ? 13 : 9}
      eventHandlers={{ click: () => onSelect(p.id) }}
      pathOptions={{
        color: selected ? "#1a1d2e" : "#ffffff",
        weight: selected ? 3 : 2,
        fillColor: p.color,
        fillOpacity: p.muted ? 0.28 : 1,
      }}
    >
      <Tooltip direction="top" offset={[0, -6]}>
        <div className="text-xs">
          <p className="font-semibold">{p.label}</p>
          {p.sub && <p className="opacity-70">{p.sub}</p>}
        </div>
      </Tooltip>
    </CircleMarker>
  );
}

function ClusterBubble({
  lat,
  lng,
  count,
  onClick,
}: {
  lat: number;
  lng: number;
  count: number;
  onClick: () => void;
}) {
  // Bubble grows with the (log-scaled) number of communes it stands for.
  const radius = 14 + Math.min(20, Math.log2(count) * 3);
  return (
    <CircleMarker
      center={[lat, lng]}
      radius={radius}
      eventHandlers={{ click: onClick }}
      pathOptions={{
        color: "#ffffff",
        weight: 2,
        fillColor: "#3b6ef5",
        fillOpacity: 0.9,
      }}
    >
      <Tooltip permanent direction="center" className="cluster-label">
        {count}
      </Tooltip>
    </CircleMarker>
  );
}

type Cluster =
  | { kind: "leaf"; point: MapPoint }
  | { kind: "cluster"; id: string; lat: number; lng: number; count: number };

function ClusteredMarkers({
  points,
  selectedId,
  onSelect,
}: {
  points: MapPoint[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const map = useMap();
  // Bump on viewport changes so the clustering recomputes against the new
  // zoom/pan (pixel positions shift with both).
  const [view, setView] = useState(0);
  useMapEvents({
    moveend: () => setView((v) => v + 1),
    zoomend: () => setView((v) => v + 1),
  });

  const clusters = useMemo<Cluster[]>(() => {
    const padded = map.getBounds().pad(0.25); // keep edge markers as you pan
    const buckets = new Map<string, MapPoint[]>();
    const out: Cluster[] = [];
    for (const p of points) {
      if (!padded.contains([p.lat, p.lng])) continue;
      // The selected commune always stays a visible, clickable leaf.
      if (p.id === selectedId) {
        out.push({ kind: "leaf", point: p });
        continue;
      }
      const px = map.latLngToContainerPoint([p.lat, p.lng]);
      const key = `${Math.floor(px.x / CLUSTER_CELL_PX)}:${Math.floor(px.y / CLUSTER_CELL_PX)}`;
      const arr = buckets.get(key);
      if (arr) arr.push(p);
      else buckets.set(key, [p]);
    }
    for (const [key, arr] of buckets) {
      if (arr.length === 1) {
        out.push({ kind: "leaf", point: arr[0] });
        continue;
      }
      let sumLat = 0;
      let sumLng = 0;
      for (const p of arr) {
        sumLat += p.lat;
        sumLng += p.lng;
      }
      out.push({
        kind: "cluster",
        id: key,
        lat: sumLat / arr.length,
        lng: sumLng / arr.length,
        count: arr.length,
      });
    }
    return out;
    // `view` is the recompute trigger; map methods read current viewport.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [points, selectedId, view, map]);

  return (
    <>
      {clusters.map((c) =>
        c.kind === "leaf" ? (
          <LeafMarker
            key={c.point.id}
            p={c.point}
            selected={c.point.id === selectedId}
            onSelect={onSelect}
          />
        ) : (
          <ClusterBubble
            key={`cl-${c.id}`}
            lat={c.lat}
            lng={c.lng}
            count={c.count}
            onClick={() =>
              map.flyTo([c.lat, c.lng], Math.min(map.getZoom() + 2, 16), {
                duration: 0.5,
              })
            }
          />
        ),
      )}
    </>
  );
}

export default function FranceMap({
  points,
  fitKey = "default",
  frameBounds,
  geojson,
  cityByCode,
  colorMode,
  gares = [],
  showGares = false,
  selectedId,
  onSelect,
}: {
  points: MapPoint[];
  /** Identifies the geographic set so the map refits only when it changes. */
  fitKey?: string;
  /** Fixed framing box for the current scope; falls back to the points' box. */
  frameBounds?: BBox;
  /** When provided (IDF, commune view): render a choropleth instead of points. */
  geojson?: FeatureCollection | null;
  cityByCode?: Map<string, ScoredCity>;
  colorMode?: ColorMode;
  gares?: Gare[];
  showGares?: boolean;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const choropleth = geojson != null && cityByCode != null && colorMode != null;
  const isDark = useIsDark();
  const tiles = isDark ? TILES.dark : TILES.light;

  return (
    <MapContainer
      center={[48.8566, 2.3522]}
      zoom={10}
      scrollWheelZoom
      preferCanvas // render markers on a canvas — keeps thousands of points smooth
      className="h-full w-full"
      style={{ background: isDark ? "#13151c" : "#f4f5f9" }}
    >
      <TileLayer
        key={isDark ? "dark" : "light"}
        attribution={tiles.attribution}
        url={tiles.url}
      />
      <FitBounds points={points} fitKey={fitKey} box={frameBounds} />
      <FlyToSelected points={points} selectedId={selectedId} />

      {choropleth && (
        <ChoroplethLayer
          geojson={geojson}
          cityByCode={cityByCode}
          mode={colorMode}
          selectedId={selectedId}
          onSelect={onSelect}
        />
      )}

      {/* Gares layer (over the choropleth / under nothing). */}
      {showGares &&
        gares
          .filter((g) => g.latitude != null && g.longitude != null)
          .map((g) => (
            <CircleMarker
              key={`gare-${g.code_uic}`}
              center={[g.latitude!, g.longitude!]}
              radius={4}
              pathOptions={{
                color: "#0f172a",
                weight: 1,
                fillColor: "#1e293b",
                fillOpacity: 0.85,
              }}
            >
              <Tooltip>
                <span className="text-xs font-medium">🚆 {g.nom_gare}</span>
              </Tooltip>
            </CircleMarker>
          ))}

      {/* Point markers — used when there's no choropleth (France scope / drill).
          Large sets (France scope) are clustered; small sets render directly. */}
      {!choropleth && points.length > CLUSTER_THRESHOLD && (
        <ClusteredMarkers
          points={points}
          selectedId={selectedId}
          onSelect={onSelect}
        />
      )}
      {!choropleth &&
        points.length <= CLUSTER_THRESHOLD &&
        points.map((p) => (
          <LeafMarker
            key={p.id}
            p={p}
            selected={p.id === selectedId}
            onSelect={onSelect}
          />
        ))}
    </MapContainer>
  );
}
