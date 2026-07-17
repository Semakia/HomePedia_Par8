import { CartographeView } from "@/components/map/cartographe-view";
import {
  IDF_DEPARTEMENTS,
  getCities,
  getCitiesByDepartements,
  getGares,
  getGaresByDepartements,
} from "@/lib/data";

// The map is the product's home: it opens on the whole country by default; the
// user can narrow to Île-de-France via ?scope=idf.
export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<{ scope?: string }>;
}) {
  const { scope } = await searchParams;
  const france = scope !== "idf";

  // Gares match the displayed scope: nationwide (top stations by traffic) in
  // France scope, the IDF departments otherwise — never IDF-only behind a
  // France map.
  const [cities, gares] = await Promise.all([
    // France scope: pull every commune (~32k) — the map clusters them so the
    // marker count stays low. IDF scope keeps the per-department choropleth feed.
    france ? getCities({ size: 40000 }) : getCitiesByDepartements(IDF_DEPARTEMENTS),
    france ? getGares({ size: 2000 }) : getGaresByDepartements(IDF_DEPARTEMENTS),
  ]);

  return (
    <CartographeView
      cities={cities}
      gares={gares}
      scope={france ? "france" : "idf"}
    />
  );
}
