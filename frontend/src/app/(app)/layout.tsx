import { Sidebar } from "@/components/sidebar";
import { DataSourceBadge } from "@/components/data-source-badge";
import { OnboardingTour } from "@/components/onboarding/onboarding-tour";
import { auth } from "@/auth";

// Authenticated app shell: persistent sidebar + main content. Everything under
// this route group is gated by proxy.ts, so reaching here implies a session; we
// still read it to feed the sidebar user chip. The (auth) group (login/register)
// deliberately renders outside this shell.
export default async function AppLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const session = await auth();

  return (
    <>
      <DataSourceBadge />
      <OnboardingTour />
      <div className="flex min-h-screen">
        <Sidebar user={session?.user ?? null} />
        <div className="flex min-w-0 flex-1 flex-col">
          <main className="flex-1 px-8 py-6">{children}</main>
        </div>
      </div>
    </>
  );
}
