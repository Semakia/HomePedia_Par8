// First-launch onboarding tour — persisted state + the ordered step script.
// Mirrors the storage pattern of src/lib/preferences.ts (localStorage, SSR-safe).
// See onboarding-provider.tsx (store/hook) and onboarding-tour.tsx (overlay).

export type TourRoute = "/" | "/statistiques" | "/tableau" | "/analyse";

// `target` is the value of a `data-tour="..."` attribute placed on the element to
// spotlight; absent for centered modal steps (welcome / end).
// `advanceOn: "action"` advances when the app calls notify(<step.id>) from a real
// user action; "next" advances via the button in the bubble.
export type TourStep = {
  id: string;
  route: TourRoute;
  target?: string;
  title: string;
  body: string;
  /** Inline hint shown for "action" steps (what the user must do). */
  hint?: string;
  advanceOn: "action" | "next";
};

export const TOUR_STEPS: TourStep[] = [
  {
    id: "welcome",
    route: "/",
    title: "Bienvenue sur Homepedia 👋",
    body: "Trouvez où acheter à Paris et en Île-de-France en 3 étapes : vos critères, une ville recommandée, ses statistiques. Laissez-vous guider.",
    advanceOn: "next",
  },
  {
    id: "criteria",
    route: "/",
    target: "criteria",
    title: "1. Vos critères",
    body: "Renseignez votre budget, la surface souhaitée et ce qui compte le plus pour vous (transport, services…). La carte se met à jour en direct. Cliquez « Suivant » quand vous avez terminé.",
    advanceOn: "next",
  },
  {
    id: "recommendations",
    route: "/",
    target: "recommendations",
    title: "2. Les villes recommandées",
    body: "Voici les communes qui correspondent le mieux à vos critères, classées par score. Cliquez-en une pour la découvrir.",
    hint: "→ Cliquez une commune recommandée",
    advanceOn: "action",
  },
  {
    id: "fiche",
    route: "/",
    target: "fiche",
    title: "La fiche de la ville",
    body: "Son score détaillé, le prix au m², la desserte transport, les équipements et le profil de population — tout en un coup d'œil.",
    advanceOn: "next",
  },
  {
    id: "view-stats",
    route: "/",
    target: "view-stats",
    title: "3. L'analyse complète",
    body: "Pour aller plus loin, ouvrez les statistiques détaillées de la ville.",
    hint: "→ Cliquez « Voir les statistiques »",
    advanceOn: "action",
  },
  {
    id: "stats",
    route: "/statistiques",
    target: "stats",
    title: "Les statistiques détaillées",
    body: "Évolution des prix, répartition par type de bien, démographie et équipements : de quoi décider en confiance.",
    advanceOn: "next",
  },
  {
    id: "goto-tableau",
    route: "/statistiques",
    target: "nav-tableau",
    title: "Comparez tous les arrondissements",
    body: "Envie de tout voir d'un coup ? Le tableau met côte à côte les arrondissements de Paris, Lyon et Marseille.",
    hint: "→ Cliquez « Tableau » dans le menu",
    advanceOn: "action",
  },
  {
    id: "tableau",
    route: "/tableau",
    target: "tableau-table",
    title: "Le tableau comparatif",
    body: "Prix, revenus, population et abordabilité de chaque arrondissement. Triez n'importe quelle colonne, filtrez par ville, exportez le tout en CSV.",
    advanceOn: "next",
  },
  {
    id: "goto-analyse",
    route: "/tableau",
    target: "nav-analyse",
    title: "Besoin d'un avis en clair ?",
    body: "L'onglet Analyse résume une ville en quelques phrases : abordabilité, prix, transport, équipements et profil de population.",
    hint: "→ Cliquez « Analyse » dans le menu",
    advanceOn: "action",
  },
  {
    id: "analyse",
    route: "/analyse",
    target: "analyse-report",
    title: "L'analyse rédigée",
    body: "Une synthèse générée à partir des données, comparée à la moyenne nationale. Changez de ville avec la recherche en haut à droite.",
    advanceOn: "next",
  },
  {
    id: "end",
    route: "/analyse",
    title: "Vous êtes prêt ! 🎉",
    body: "Vous connaissez le parcours. Explorez librement la carte, changez de mode de couleur, affichez les gares… Bonne recherche !",
    advanceOn: "next",
  },
];

export type OnboardingState = {
  /** The tour has been completed or skipped — don't auto-start again. */
  seen: boolean;
  /** Whether the tour is currently running. */
  active: boolean;
  /** Index into TOUR_STEPS. */
  step: number;
};

export const DEFAULT_ONBOARDING: OnboardingState = {
  seen: false,
  active: false,
  step: 0,
};

export const STORAGE_KEY = "homepedia:onboarding";

export function loadOnboarding(): OnboardingState {
  if (typeof window === "undefined") return DEFAULT_ONBOARDING;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_ONBOARDING;
    const merged = {
      ...DEFAULT_ONBOARDING,
      ...(JSON.parse(raw) as Partial<OnboardingState>),
    };
    // Guard against a stored step index that no longer exists (script changed).
    if (merged.step < 0 || merged.step >= TOUR_STEPS.length) {
      merged.step = 0;
      merged.active = false;
    }
    return merged;
  } catch {
    return DEFAULT_ONBOARDING;
  }
}

export function saveOnboarding(state: OnboardingState): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // localStorage unavailable (private mode, quota) — ignore.
  }
}
