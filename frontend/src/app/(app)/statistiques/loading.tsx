import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

// Instant fallback for /statistiques while the Server Component fetches the
// city detail + housing + cities list. Mirrors the page's grids (KPIs row +
// three lg:grid-cols-3 sections).
export default function StatistiquesLoading() {
  return (
    <div className="flex flex-col gap-6">
      {/* Header + search */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-col gap-2">
          <Skeleton className="h-7 w-40" />
          <Skeleton className="h-4 w-32" />
        </div>
        <Skeleton className="h-10 w-64" />
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i} className="flex flex-col gap-2">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-6 w-24" />
          </Card>
        ))}
      </div>

      {/* Two 2/3 + 1/3 rows */}
      {Array.from({ length: 2 }).map((_, row) => (
        <div key={row} className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <ChartCard className="lg:col-span-2" />
          <ChartCard />
        </div>
      ))}

      {/* Three equal cards */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <ChartCard key={i} />
        ))}
      </div>
    </div>
  );
}

function ChartCard({ className = "" }: { className?: string }) {
  return (
    <Card className={`flex flex-col gap-4 ${className}`}>
      <Skeleton className="h-5 w-40" />
      <Skeleton className="h-48 w-full" />
    </Card>
  );
}
