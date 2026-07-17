import Link from "next/link";

// Full-screen shell for auth screens — deliberately outside the (app) sidebar
// layout. Centered card on the app background; theme tokens keep it consistent
// in light/dark.
export default function AuthLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-bg px-4 py-10">
      <Link
        href="/"
        className="mb-8 flex items-center gap-2"
        aria-label="HOMEPEDIA"
      >
        <span className="grid h-9 w-9 place-items-center rounded-lg bg-primary text-sm font-bold text-white">
          H
        </span>
        <span className="text-lg font-semibold tracking-tight text-ink">
          HOMEPEDIA
        </span>
      </Link>
      <div className="w-full max-w-sm rounded-2xl border border-line bg-card p-6 shadow-sm">
        {children}
      </div>
    </div>
  );
}
