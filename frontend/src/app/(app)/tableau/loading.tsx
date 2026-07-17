import { Skeleton } from "@/components/ui/skeleton";

// Instant fallback for /tableau while the Server Component fetches the
// arrondissement rows. Mirrors the page: header + controls + table shell.
export default function TableauLoading() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <Skeleton className="h-7 w-72" />
        <Skeleton className="h-4 w-96" />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-10 w-64" />
      </div>

      <div className="rounded-2xl border border-line bg-card p-4">
        {Array.from({ length: 10 }).map((_, i) => (
          <Skeleton key={i} className="mb-3 h-8 w-full last:mb-0" />
        ))}
      </div>
    </div>
  );
}
