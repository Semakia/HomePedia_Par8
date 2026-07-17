import Link from "next/link";
import { Globe, MapPin } from "lucide-react";

/**
 * Header switch between the per-city stats and the France-wide aggregate.
 * Server-friendly (no hooks): the stats page passes `active` from its `scope`
 * search param. When France is active, the link goes back to the default city.
 */
export function NationalToggle({ active }: { active: boolean }) {
  const href = active ? "/statistiques" : "/statistiques?scope=france";
  const Icon = active ? MapPin : Globe;
  const label = active ? "Revenir à une ville" : "France entière";

  return (
    <Link
      href={href}
      className={`flex shrink-0 items-center gap-2 rounded-xl border px-3 py-2.5 text-sm font-medium transition-colors ${
        active
          ? "border-primary bg-primary/10 text-primary"
          : "border-line bg-card text-muted hover:border-primary/40 hover:text-ink"
      }`}
    >
      <Icon size={16} />
      {label}
    </Link>
  );
}
