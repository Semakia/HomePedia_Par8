import { prisma } from "@/lib/prisma";
import { asRole } from "@/lib/auth-roles";
import { Card } from "@/components/ui/card";

// Overview tab of the admin section. Access is gated by admin/layout.tsx.
// Real-time counts — no cache.
export const dynamic = "force-dynamic";

function daysAgo(n: number): Date {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d;
}

export default async function AdminOverviewPage() {
  const [total, admins, last7, last30, recent] = await Promise.all([
    prisma.user.count(),
    prisma.user.count({ where: { role: "ADMIN" } }),
    prisma.user.count({ where: { createdAt: { gte: daysAgo(7) } } }),
    prisma.user.count({ where: { createdAt: { gte: daysAgo(30) } } }),
    prisma.user.findMany({
      orderBy: { createdAt: "desc" },
      take: 5,
      select: { id: true, email: true, name: true, role: true, createdAt: true },
    }),
  ]);

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label="Comptes" value={total.toLocaleString("fr-FR")} />
        <Kpi
          label="Administrateurs"
          value={admins.toLocaleString("fr-FR")}
          sub={`${(total - admins).toLocaleString("fr-FR")} utilisateur(s)`}
        />
        <Kpi
          label="Inscrits (7 j)"
          value={last7.toLocaleString("fr-FR")}
        />
        <Kpi
          label="Inscrits (30 j)"
          value={last30.toLocaleString("fr-FR")}
        />
      </div>

      <div className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold text-ink">Dernières inscriptions</h2>
        <Card className="overflow-x-auto p-0">
          <table className="w-full min-w-[480px] text-sm">
            <thead>
              <tr className="border-b border-line text-left text-xs uppercase tracking-wider text-muted">
                <th className="px-5 py-3 font-semibold">Nom</th>
                <th className="px-5 py-3 font-semibold">Email</th>
                <th className="px-5 py-3 font-semibold">Rôle</th>
                <th className="px-5 py-3 font-semibold">Inscrit le</th>
              </tr>
            </thead>
            <tbody>
              {recent.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-5 py-8 text-center text-muted">
                    Aucun compte enregistré.
                  </td>
                </tr>
              ) : (
                recent.map((u) => (
                  <tr key={u.id} className="border-b border-line/60 last:border-0">
                    <td className="px-5 py-3 text-ink">{u.name || "—"}</td>
                    <td className="px-5 py-3 text-muted">{u.email}</td>
                    <td className="px-5 py-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          asRole(u.role) === "ADMIN"
                            ? "bg-primary-soft text-primary"
                            : "bg-bg text-muted"
                        }`}
                      >
                        {asRole(u.role) === "ADMIN" ? "Administrateur" : "Utilisateur"}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-muted">
                      {u.createdAt.toLocaleDateString("fr-FR")}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </Card>
      </div>
    </div>
  );
}

function Kpi({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <Card className="!p-4">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 truncate text-lg font-semibold text-ink" title={value}>
        {value}
      </p>
      {sub && <p className="text-[11px] text-muted">{sub}</p>}
    </Card>
  );
}
