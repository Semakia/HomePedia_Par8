import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { PreferencesProvider } from "@/components/preferences-provider";

// Applies stored preferences (theme/density/badge) to <html> before the first
// paint to avoid a flash of the wrong theme (FOUC). Mirrors applyPreferences()
// in src/lib/preferences.ts — keep the two in sync.
const PREFS_BOOTSTRAP = `(function(){try{var d=document.documentElement;var p=JSON.parse(localStorage.getItem("homepedia:prefs")||"{}");var t=p.theme||"system";var dark=t==="dark"||(t==="system"&&matchMedia("(prefers-color-scheme: dark)").matches);d.classList.toggle("dark",dark);d.dataset.density=p.density||"comfortable";d.dataset.badge=p.showBadge===false?"off":"on";}catch(e){}})();`;

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Homepedia",
  description: "Plateforme d'analyse de l'immobilier français",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    // suppressHydrationWarning: the PREFS_BOOTSTRAP script mutates <html>
    // (dark class + data-density/data-badge) before hydration, so its attributes
    // intentionally differ from the server markup.
    <html
      lang="fr"
      className={`${inter.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: PREFS_BOOTSTRAP }} />
      </head>
      <body className="min-h-full font-sans">
        {/* The app shell (sidebar + main) lives in the (app) route group layout.
            Auth screens in the (auth) group render full-screen. */}
        <PreferencesProvider>{children}</PreferencesProvider>
      </body>
    </html>
  );
}
