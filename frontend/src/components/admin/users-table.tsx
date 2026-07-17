"use client";

import { useMemo, useState, useTransition } from "react";
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  Search,
  ShieldCheck,
  ShieldOff,
  Trash2,
} from "lucide-react";

import { asRole } from "@/lib/auth-roles";
import { deleteUser, setUserRole } from "@/app/(app)/admin/actions";

export type UserRow = {
  id: string;
  email: string;
  name: string | null;
  role: string;
  createdAt: Date;
};

type Align = "left" | "right";
type Column = {
  key: string;
  label: string;
  align: Align;
  sortValue: (r: UserRow) => number | string | null;
  render: (r: UserRow) => React.ReactNode;
};

const COLUMNS: Column[] = [
  {
    key: "name",
    label: "Nom",
    align: "left",
    sortValue: (r) => r.name?.toLowerCase() ?? "",
    render: (r) => <span className="font-medium text-ink">{r.name || "—"}</span>,
  },
  {
    key: "email",
    label: "Email",
    align: "left",
    sortValue: (r) => r.email.toLowerCase(),
    render: (r) => <span className="text-muted">{r.email}</span>,
  },
  {
    key: "role",
    label: "Rôle",
    align: "left",
    sortValue: (r) => asRole(r.role),
    render: (r) => (
      <span
        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
          asRole(r.role) === "ADMIN"
            ? "bg-primary-soft text-primary"
            : "bg-bg text-muted"
        }`}
      >
        {asRole(r.role) === "ADMIN" ? "Administrateur" : "Utilisateur"}
      </span>
    ),
  },
  {
    key: "createdAt",
    label: "Inscrit le",
    align: "left",
    sortValue: (r) => r.createdAt.getTime(),
    render: (r) => (
      <span className="text-muted">{r.createdAt.toLocaleDateString("fr-FR")}</span>
    ),
  },
];

function compare(a: number | string | null, b: number | string | null, order: "asc" | "desc") {
  if (a == null && b == null) return 0;
  if (a == null) return 1;
  if (b == null) return -1;
  const cmp =
    typeof a === "number" && typeof b === "number"
      ? a - b
      : String(a).localeCompare(String(b), "fr");
  return order === "asc" ? cmp : -cmp;
}

export function UsersTable({
  rows,
  currentUserId,
}: {
  rows: UserRow[];
  currentUserId: string;
}) {
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState("createdAt");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [error, setError] = useState<string | null>(null);
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const col = COLUMNS.find((c) => c.key === sortKey) ?? COLUMNS[3];
    return rows
      .filter((r) =>
        q === ""
          ? true
          : r.email.toLowerCase().includes(q) ||
            (r.name?.toLowerCase().includes(q) ?? false),
      )
      .sort((a, b) => compare(col.sortValue(a), col.sortValue(b), order));
  }, [rows, query, sortKey, order]);

  const onSort = (key: string) => {
    if (key === sortKey) {
      setOrder((o) => (o === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setOrder(key === "createdAt" ? "desc" : "asc");
    }
  };

  const run = (id: string, fn: () => Promise<string | undefined>) => {
    setError(null);
    setBusyId(id);
    startTransition(async () => {
      const message = await fn();
      setBusyId(null);
      setConfirmId(null);
      if (message) setError(message);
    });
  };

  const toggleRole = (r: UserRow) =>
    run(r.id, () => setUserRole(r.id, asRole(r.role) === "ADMIN" ? "USER" : "ADMIN"));

  const remove = (r: UserRow) => run(r.id, () => deleteUser(r.id));

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="relative">
          <Search
            size={15}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
          />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Rechercher un compte…"
            className="w-64 rounded-xl border border-line bg-card py-2 pl-9 pr-3 text-sm outline-none focus:border-primary/50"
          />
        </div>
        <p className="text-xs text-muted">
          {filtered.length} compte{filtered.length > 1 ? "s" : ""}
        </p>
      </div>

      {error && (
        <p
          role="alert"
          className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/40"
        >
          {error}
        </p>
      )}

      <div className="overflow-x-auto rounded-2xl border border-line bg-card">
        <table className="w-full min-w-[720px] border-collapse text-sm">
          <thead>
            <tr className="border-b border-line">
              {COLUMNS.map((col) => {
                const active = col.key === sortKey;
                const Icon = active ? (order === "asc" ? ArrowUp : ArrowDown) : ArrowUpDown;
                return (
                  <th
                    key={col.key}
                    aria-sort={active ? (order === "asc" ? "ascending" : "descending") : "none"}
                    className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider"
                  >
                    <button
                      type="button"
                      onClick={() => onSort(col.key)}
                      className={`inline-flex items-center gap-1.5 transition-colors hover:text-ink ${
                        active ? "text-primary" : "text-muted/70"
                      }`}
                    >
                      {col.label}
                      <Icon size={13} className={active ? "opacity-100" : "opacity-40"} />
                    </button>
                  </th>
                );
              })}
              <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-muted/70">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={COLUMNS.length + 1} className="px-4 py-10 text-center text-muted">
                  Aucun compte ne correspond à votre recherche.
                </td>
              </tr>
            ) : (
              filtered.map((r) => {
                const isSelf = r.id === currentUserId;
                const isBusy = pending && busyId === r.id;
                return (
                  <tr key={r.id} className="border-b border-line/60 last:border-0 hover:bg-bg">
                    {COLUMNS.map((col) => (
                      <td key={col.key} className="px-4 py-3">
                        {col.render(r)}
                      </td>
                    ))}
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        {isSelf ? (
                          <span className="text-xs italic text-muted">Vous</span>
                        ) : (
                          <>
                            <button
                              type="button"
                              onClick={() => toggleRole(r)}
                              disabled={isBusy}
                              className="inline-flex items-center gap-1.5 rounded-lg border border-line px-2.5 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-primary-soft disabled:opacity-50"
                            >
                              {asRole(r.role) === "ADMIN" ? (
                                <>
                                  <ShieldOff size={13} /> Rétrograder
                                </>
                              ) : (
                                <>
                                  <ShieldCheck size={13} /> Promouvoir
                                </>
                              )}
                            </button>
                            {confirmId === r.id ? (
                              <button
                                type="button"
                                onClick={() => remove(r)}
                                disabled={isBusy}
                                className="inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-2.5 py-1.5 text-xs font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                              >
                                <Trash2 size={13} /> Confirmer
                              </button>
                            ) : (
                              <button
                                type="button"
                                onClick={() => setConfirmId(r.id)}
                                className="inline-flex items-center gap-1.5 rounded-lg border border-line px-2.5 py-1.5 text-xs font-medium text-red-600 transition-colors hover:bg-red-50 dark:hover:bg-red-950/40"
                              >
                                <Trash2 size={13} /> Supprimer
                              </button>
                            )}
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
