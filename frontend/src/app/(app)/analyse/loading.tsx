import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

// Instant fallback for /analyse while the Server Component fetches the city
// detail + national baseline. Mirrors the page: header + lead card + insight grid.
export default function AnalyseLoading() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-col gap-2">
          <Skeleton className="h-7 w-32" />
          <Skeleton className="h-4 w-80" />
        </div>
        <Skeleton className="h-11 w-80" />
      </div>

      <Card className="flex gap-3">
        <Skeleton className="h-9 w-9 shrink-0 rounded-xl" />
        <div className="flex flex-1 flex-col gap-2">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <Card key={i} className="flex gap-3 p-5">
            <Skeleton className="h-9 w-9 shrink-0 rounded-xl" />
            <div className="flex flex-1 flex-col gap-2">
              <Skeleton className="h-4 w-28" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-3/4" />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
