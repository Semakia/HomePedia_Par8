import { AmenitiesCard } from "@/components/charts/amenities-card";
import { CityKpis } from "@/components/charts/city-kpis";
import { DemographicsCard } from "@/components/charts/demographics-card";
import { HousingPriceCard } from "@/components/charts/housing-price-card";
import { MatchRadarCard } from "@/components/charts/match-radar-card";
import { PriceCard } from "@/components/charts/price-card";
import { RepartitionCard } from "@/components/charts/repartition-card";
import { SearchCity } from "@/components/charts/search-city";
import { NationalToggle } from "@/components/charts/national-toggle";
import { YearlyPriceCard } from "@/components/charts/yearly-price-card";
import {
  getCities,
  getCityDetail,
  getHousingByType,
  getNationalDetail,
  getNationalHousing,
} from "@/lib/data";

// Default city = Paris; the search bar and the map's "Voir les statistiques"
// button switch it via ?ville=<code_commune>.
const DEFAULT_COMMUNE = "75056";

export default async function StatistiquesPage({
  searchParams,
}: {
  searchParams: Promise<{ ville?: string; scope?: string }>;
}) {
  const { ville, scope } = await searchParams;
  // "France entière" = a national aggregate shaped like a city, so the whole
  // per-city layout below is reused unchanged (titles read detail.nom_commune).
  const national = scope === "france";
  const code = ville ?? DEFAULT_COMMUNE;

  const [detail, housing, cities] = await Promise.all([
    national ? getNationalDetail() : getCityDetail(code),
    national ? getNationalHousing() : getHousingByType({ code_commune: code }),
    // Only feeds the search box (client-side filtered).
    getCities({ size: 200 }),
  ]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Statistiques</h1>
          <p className="text-sm text-muted">
            {national
              ? "France entière · agrégat pondéré, toutes communes"
              : `${detail.nom_commune} · dépt ${detail.code_departement}`}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <NationalToggle active={national} />
          <SearchCity cities={cities} current={national ? "" : code} />
        </div>
      </div>

      <div className="flex flex-col gap-6" data-tour="stats">
        <CityKpis detail={detail} national={national} />

        {/* Prix & marché */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <PriceCard detail={detail} />
          </div>
          <RepartitionCard rows={housing} />
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <YearlyPriceCard detail={detail} />
          </div>
          <HousingPriceCard rows={housing} />
        </div>

        {/* Démographie & cadre de vie + correspondance.
            En mode pays, seule la démographie est pertinente : les services et
            la correspondance (persona) n'ont pas de sens agrégés au national. */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <DemographicsCard detail={detail} />
          {!national && <AmenitiesCard detail={detail} />}
          {!national && <MatchRadarCard detail={detail} />}
        </div>
      </div>
    </div>
  );
}
