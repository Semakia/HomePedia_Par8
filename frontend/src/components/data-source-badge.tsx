// Fixed top-right indicator showing whether the page is rendered from live API
// data or the mock fallback (src/lib/data.ts). Async Server Component: the
// live/mock probe runs at SSR time, never in the browser.
import { getDataSource } from "@/lib/data";

export async function DataSourceBadge() {
  const isMock = (await getDataSource()) === "mock";

  return (
    <div className="data-source-badge fixed right-4 top-4 z-50">
      <span
        className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium shadow-sm ${
          isMock
            ? "border-amber-300 bg-amber-50 text-amber-700"
            : "border-emerald-300 bg-emerald-50 text-emerald-700"
        }`}
        title={
          isMock
            ? "L'API est injoignable ou la couche Gold est vide — données de démonstration."
            : "Données servies par l'API Gold."
        }
      >
        <span
          className={`h-1.5 w-1.5 rounded-full ${isMock ? "bg-amber-500" : "bg-emerald-500"}`}
        />
        {isMock ? "Données mockées" : "Données live"}
      </span>
    </div>
  );
}
