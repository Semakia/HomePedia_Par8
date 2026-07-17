import type { ReactNode } from "react";

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-2xl border border-line bg-card p-6 ${className}`}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  action,
}: {
  title: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="mb-4 flex items-start justify-between gap-4">
      <div>{title}</div>
      {action}
    </div>
  );
}

export function ReportButton() {
  return (
    <button
      type="button"
      className="rounded-lg border border-line px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary-soft"
    >
      Voir rapport
    </button>
  );
}
