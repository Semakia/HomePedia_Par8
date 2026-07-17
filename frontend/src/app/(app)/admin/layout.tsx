import type { ReactNode } from "react";
import { redirect } from "next/navigation";

import { auth } from "@/auth";
import { isAdmin } from "@/lib/auth-roles";
import { AdminTabs } from "@/components/admin/admin-tabs";

// Admin section shell. proxy.ts already gates /admin* on role, but we re-check
// here so every admin route is safe even if the matcher ever changes (defence
// in depth). The check covers all nested pages under this layout.
export default async function AdminLayout({
  children,
}: {
  children: ReactNode;
}) {
  const session = await auth();
  if (!isAdmin(session?.user?.role)) redirect("/");

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-1">
        <h1 className="text-xl font-semibold text-ink">Administration</h1>
        <p className="text-sm text-muted">
          Gestion des comptes et supervision du serveur.
        </p>
      </div>

      <AdminTabs />

      {children}
    </div>
  );
}
