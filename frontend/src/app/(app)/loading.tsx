import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

// Instant fallback for the map route (src/app/page.tsx) while its Server
// Component fetches cities + gares. Mirrors CartographeView's layout
// (header + lg:grid-cols-[300px_1fr_320px]) so nothing jumps when data lands.
export default function MapLoading() {
  return (
    <div className="flex flex-col gap-5">
      {/* Header */}
      <div className="flex flex-col gap-2">
        <Skeleton className="h-7 w-40" />
        <Skeleton className="h-4 w-72" />
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[300px_1fr_320px] lg:items-start">
        {/* Criteria panel */}
        <Card className="order-2 flex flex-col gap-4 lg:order-1">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-px w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-px w-full" />
          <Skeleton className="h-3 w-40" />
          <Skeleton className="h-2 w-full" />
          <Skeleton className="h-2 w-full" />
          <Skeleton className="h-2 w-full" />
        </Card>

        {/* Map */}
        <div className="order-1 flex flex-col gap-3 lg:order-2">
          <div className="flex flex-wrap items-center gap-2">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="ml-auto h-8 w-32" />
          </div>
          <Skeleton className="h-[600px] w-full rounded-2xl" />
        </div>

        {/* Recommendations */}
        <Card className="order-3 flex flex-col gap-3">
          <Skeleton className="h-5 w-36" />
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </Card>
      </div>
    </div>
  );
}
