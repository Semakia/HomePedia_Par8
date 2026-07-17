import { ArrondissementsTable } from "@/components/table/arrondissements-table";
import { getArrondissements } from "@/lib/data";

// Tabular deliverable: a sortable/filterable comparison of every arrondissement
// (Paris, Lyon, Marseille) straight from market.arrondissement_metrics — the
// only Gold table with sub-commune granularity. Complements the map (carto) and
// the charts (dataviz).
export default async function TableauPage() {
  // No department filter → the API returns all 45 arrondissements across the
  // three departments; the client component filters/sorts in place.
  const rows = await getArrondissements({ size: 200 });

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold">Tableau des arrondissements</h1>
        <p className="text-sm text-muted">
          Comparez prix, revenus, démographie et abordabilité — triez chaque colonne, filtrez par ville.
        </p>
      </div>

      <div data-tour="tableau-table">
        <ArrondissementsTable rows={rows} />
      </div>
    </div>
  );
}
