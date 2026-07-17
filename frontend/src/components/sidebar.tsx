"use client";

import Link, { useLinkStatus } from "next/link";
import { usePathname } from "next/navigation";
import { notify } from "./onboarding/onboarding-provider";
import { logout } from "@/app/(app)/actions";
import { isAdmin, type Role } from "@/lib/auth-roles";
import {
  Map,
  BarChart3,
  Table2,
  FileText,
  Settings,
  HelpCircle,
  ShieldCheck,
  LogOut,
  LogIn,
  type LucideIcon,
} from "lucide-react";

export type SidebarUser = {
  name?: string | null;
  email?: string | null;
  role?: Role;
} | null;

// `tour`: value of the data-tour attribute so the onboarding tour can spotlight
// this link. `tourEvent`: id fired via notify() on click, to advance an
// action-driven tour step (e.g. "go to the table").
type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  tour?: string;
  tourEvent?: string;
};

const MENU: NavItem[] = [
  { href: "/", label: "Cartographe", icon: Map },
  { href: "/statistiques", label: "Statistiques", icon: BarChart3 },
  {
    href: "/tableau",
    label: "Tableau",
    icon: Table2,
    tour: "nav-tableau",
    tourEvent: "goto-tableau",
  },
  {
    href: "/analyse",
    label: "Analyse",
    icon: FileText,
    tour: "nav-analyse",
    tourEvent: "goto-analyse",
  },
];

const OTHERS: NavItem[] = [
  { href: "/parametres", label: "Paramètres", icon: Settings },
  { href: "/aide", label: "Aide", icon: HelpCircle },
];

function NavLink({ item, active }: { item: NavItem; active: boolean }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      data-tour={item.tour}
      onClick={() => item.tourEvent && notify(item.tourEvent)}
      className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
        active
          ? "bg-primary-soft text-primary"
          : "text-muted hover:bg-primary-soft/60 hover:text-ink"
      }`}
    >
      <NavPending />
      <Icon size={18} strokeWidth={2} />
      {item.label}
    </Link>
  );
}

// Rendered inside <Link>, so useLinkStatus() reads that link's navigation state.
// While the click's navigation is pending (until the route's loading.tsx /
// content is ready), show a thin indeterminate bar pinned to the top of the
// viewport. Only one link is ever pending at a time, so a single bar shows.
function NavPending() {
  const { pending } = useLinkStatus();
  if (!pending) return null;
  return <span className="nav-progress-bar" aria-hidden />;
}

export function Sidebar({ user }: { user: SidebarUser }) {
  const pathname = usePathname();
  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  // Admin area is only advertised to admins (the route itself is also gated in
  // proxy.ts, so hiding the link is defence-in-depth, not the sole guard).
  const others: NavItem[] = isAdmin(user?.role)
    ? [{ href: "/admin", label: "Admin", icon: ShieldCheck }, ...OTHERS]
    : OTHERS;

  return (
    <aside className="sticky top-0 flex h-screen max-h-screen w-64 shrink-0 flex-col overflow-y-auto border-r border-line bg-sidebar">
      {/* Brand */}
      <div className="flex items-center gap-2 px-6 py-6">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-primary text-sm font-bold text-white">
          H
        </span>
        <span className="text-base font-semibold tracking-tight">HOMEPEDIA</span>
      </div>

      {/* Nav */}
      <nav className="flex flex-1 flex-col gap-1 px-4">
        <p className="px-3 pb-2 pt-2 text-xs font-semibold uppercase tracking-wider text-muted/70">
          Menu
        </p>
        {MENU.map((item) => (
          <NavLink key={item.href} item={item} active={isActive(item.href)} />
        ))}

        <p className="px-3 pb-2 pt-6 text-xs font-semibold uppercase tracking-wider text-muted/70">
          Autres
        </p>
        {others.map((item) => (
          <NavLink key={item.href} item={item} active={isActive(item.href)} />
        ))}
      </nav>

      {/* Footer: signed-in user + logout */}
      {user ? (
        <div className="border-t border-line px-4 py-4">
          <div className="flex items-center gap-3 rounded-xl px-2 py-2">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-primary-soft text-sm font-semibold text-primary">
              {(user.name || user.email || "?").charAt(0).toUpperCase()}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-ink">
                {user.name || user.email}
              </p>
              <p className="truncate text-xs text-muted">
                {isAdmin(user.role) ? "Administrateur" : "Utilisateur"}
              </p>
            </div>
          </div>
          <form action={logout}>
            <button
              type="submit"
              className="mt-1 flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-muted transition-colors hover:bg-primary-soft/60 hover:text-ink"
            >
              <LogOut size={18} strokeWidth={2} />
              Déconnexion
            </button>
          </form>
        </div>
      ) : (
        <div className="border-t border-line px-4 py-4">
          <Link
            href="/login"
            className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-muted transition-colors hover:bg-primary-soft/60 hover:text-ink"
          >
            <LogIn size={18} strokeWidth={2} />
            Se connecter
          </Link>
        </div>
      )}
    </aside>
  );
}
