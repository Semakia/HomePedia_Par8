"use client";

import dynamic from "next/dynamic";
import type { FeatureCollection } from "geojson";
import type { Gare } from "@/lib/api";
import type { BBox } from "@/lib/geo";
import type { ColorMode } from "@/lib/map-modes";
import type { ScoredCity } from "@/lib/scoring";
import type { MapPoint } from "./france-map";

// Leaflet touches `window` on import, so the map must render client-side only.
const FranceMap = dynamic(() => import("./france-map"), {
  ssr: false,
  loading: () => (
    <div className="grid h-full place-items-center text-sm text-muted">
      Chargement de la carte…
    </div>
  ),
});

export function CartographeMap(props: {
  points: MapPoint[];
  fitKey?: string;
  frameBounds?: BBox;
  geojson?: FeatureCollection | null;
  cityByCode?: Map<string, ScoredCity>;
  colorMode?: ColorMode;
  gares?: Gare[];
  showGares?: boolean;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return <FranceMap {...props} />;
}
