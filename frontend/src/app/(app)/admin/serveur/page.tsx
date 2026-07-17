import { CheckCircle2, XCircle } from "lucide-react";

import { api } from "@/lib/api";
import { getDataSource } from "@/lib/data";
import { prisma } from "@/lib/prisma";
import { Card } from "@/components/ui/card";

// Access is gated by admin/layout.tsx. Live probe — never cached.
export const dynamic = "force-dynamic";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

type ReadyResult =
  | { ok: true; status: string; components: Record<string, { ok: boolean; detail: string }> }
  | { ok: false; error: string };

async function probeReady(): Promise<ReadyResult> {
  try {
    // Short timeout so a hung API doesn't stall the admin page.
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 4000);
    const res = await api.ready({ signal: controller.signal });
    clearTimeout(timer);
    return { ok: true, status: res.status, components: res.components ?? {} };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : String(err) };
  }
}

export default async function AdminServerPage() {
  const [ready, source, accounts] = await Promise.all([
    probeReady(),
    getDataSource(),
    prisma.user.count(),
  ]);
  const isMock = source === "mock";

  return (
    <div className="flex flex-col gap-5">
      {/* API health */}
      <Card>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-ink">API Gold</h2>
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${
              isMock
                ? "border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-500/40 dark:bg-amber-950/40 dark:text-amber-400"
                : "border-emerald-300 bg-emerald-50 text-emerald-700 dark:border-emerald-500/40 dark:bg-emerald-950/40 dark:text-emerald-400"
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${isMock ? "bg-amber-500" : "bg-emerald-500"}`}
            />
            {isMock ? "Données mockées" : "Données live"}
          </span>
        </div>

        {ready.ok ? (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-muted">
              Statut&nbsp;: <span className="font-medium text-ink">{ready.status}</span>
            </p>
            <ul className="flex flex-col divide-y divide-line/60">
              {Object.entries(ready.components).map(([name, c]) => (
                <li key={name} className="flex items-center justify-between gap-4 py-2.5">
                  <span className="flex items-center gap-2 text-sm">
                    {c.ok ? (
                      <CheckCircle2 size={16} className="text-success" />
                    ) : (
                      <XCircle size={16} className="text-red-500" />
                    )}
                    <span className="font-medium text-ink">{name}</span>
                  </span>
                  <span className="truncate text-xs text-muted" title={c.detail}>
                    {c.detail}
                  </span>
                </li>
              ))}
              {Object.keys(ready.components).length === 0 && (
                <li className="py-2.5 text-sm text-muted">
                  Aucun composant reporté par la sonde.
                </li>
              )}
            </ul>
          </div>
        ) : (
          <div className="flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2.5 text-sm text-amber-700 dark:bg-amber-950/40 dark:text-amber-400">
            <XCircle size={16} className="mt-0.5 shrink-0" />
            <div>
              <p className="font-medium">API injoignable</p>
              <p className="mt-0.5 break-all text-xs opacity-80">{ready.error}</p>
              <p className="mt-1 text-xs opacity-80">
                Le front bascule automatiquement sur les données de démonstration.
              </p>
            </div>
          </div>
        )}
      </Card>

      {/* Environment */}
      <Card>
        <h2 className="mb-4 text-sm font-semibold text-ink">Environnement</h2>
        <dl className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
          <Info label="URL de l'API" value={API_BASE} mono />
          <Info label="Base de données" value={process.env.DATABASE_URL ?? "—"} mono />
          <Info label="Runtime Node" value={process.version} mono />
          <Info label="Comptes enregistrés" value={accounts.toLocaleString("fr-FR")} />
        </dl>
      </Card>
    </div>
  );
}

function Info({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className={`truncate text-sm text-ink ${mono ? "font-mono text-xs" : ""}`} title={value}>
        {value}
      </dd>
    </div>
  );
}
