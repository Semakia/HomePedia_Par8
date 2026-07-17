import { AnalysisReport } from "@/components/analysis/analysis-report";
import { SearchCity } from "@/components/charts/search-city";
import { buildAnalysis } from "@/lib/analysis";
import { getCities, getCityDetail, getNationalDetail } from "@/lib/data";

// Textual-analysis deliverable: a written, rule-based synthesis of a commune,
// crossing affordability + price + transport + amenities + demographics + trend.
// Complements the map (carto), the charts (dataviz) and the table (tabular).
const DEFAULT_COMMUNE = "75056"; // Paris

export default async function AnalysePage({
  searchParams,
}: {
  searchParams: Promise<{ ville?: string }>;
}) {
  const { ville } = await searchParams;
  const code = ville ?? DEFAULT_COMMUNE;

  // National aggregate = comparison baseline ("X % au-dessus de la moyenne…").
  const [detail, national, cities] = await Promise.all([
    getCityDetail(code),
    getNationalDetail(),
    getCities({ size: 200 }), // feeds the search box (client-side fallback)
  ]);

  const analysis = buildAnalysis(detail, national);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Analyse</h1>
          <p className="text-sm text-muted">
            {detail.nom_commune} · dépt {detail.code_departement} — synthèse générée à partir des indicateurs Gold
          </p>
        </div>
        <SearchCity cities={cities} current={code} basePath="/analyse" />
      </div>

      <div data-tour="analyse-report">
        <AnalysisReport analysis={analysis} />
      </div>
    </div>
  );
}
