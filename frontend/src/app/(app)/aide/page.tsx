"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  GraduationCap,
  SlidersHorizontal,
  Target,
  Palette,
  Map,
  BarChart3,
  Settings,
  Database,
  Train,
  Store,
  Users,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { start as startOnboarding } from "@/components/onboarding/onboarding-provider";
import { COLOR_MODES, legendForMode } from "@/lib/map-modes";

const STEPS: { n: string; title: string; desc: string }[] = [
  {
    n: "1",
    title: "Renseignez vos critères",
    desc: "Budget, surface, exigences de transport et d'équipement, puis ce qui compte le plus pour vous. La carte se met à jour en direct.",
  },
  {
    n: "2",
    title: "Repérez les villes recommandées",
    desc: "Les communes les mieux notées remontent en tête de liste et s'éclairent sur la carte. Cliquez-en une pour ouvrir sa fiche.",
  },
  {
    n: "3",
    title: "Analysez avant de décider",
    desc: "La fiche puis les statistiques détaillées vous donnent prix, tendance, démographie et desserte — de quoi décider en confiance.",
  },
];

const CRITERIA: { icon: LucideIcon; label: string; desc: string }[] = [
  {
    icon: Wallet,
    label: "Budget & surface",
    desc: "Votre enveloppe totale et la surface souhaitée définissent un prix au m² cible. Les communes sous ce prix sont privilégiées.",
  },
  {
    icon: Train,
    label: "Filtres durs",
    desc: "Desserte minimale, distance max à une gare et niveau d'équipement minimal écartent les communes qui ne passent pas la barre.",
  },
  {
    icon: SlidersHorizontal,
    label: "Pondérations",
    desc: "Les curseurs « ce qui compte le plus » règlent le poids de chaque dimension (budget, transport, services, ambiance jeune) dans le score.",
  },
];

const DIMENSIONS: { icon: LucideIcon; label: string; desc: string }[] = [
  {
    icon: Wallet,
    label: "Abordabilité",
    desc: "Le prix au m² comparé à votre budget cible (ou la classe d'abordabilité de la commune si vous n'avez pas saisi de budget).",
  },
  {
    icon: Train,
    label: "Transport",
    desc: "Qualité de la desserte ferroviaire et distance à la gare la plus proche.",
  },
  {
    icon: Store,
    label: "Services",
    desc: "Niveau d'équipement de la commune : commerces, santé, écoles, sport et culture.",
  },
  {
    icon: Users,
    label: "Ambiance jeune",
    desc: "Part d'actifs et de jeunes dans la population de la commune.",
  },
];

const PAGES: { icon: LucideIcon; href: string; label: string; desc: string }[] = [
  {
    icon: Map,
    href: "/",
    label: "Cartographe",
    desc: "La carte interactive : vos critères à gauche, les recommandations et la fiche à droite. Le cœur de l'outil.",
  },
  {
    icon: BarChart3,
    href: "/statistiques",
    label: "Statistiques",
    desc: "L'analyse détaillée d'une ville : évolution des prix, répartition par type de bien, démographie et équipements.",
  },
  {
    icon: Settings,
    href: "/parametres",
    label: "Paramètres",
    desc: "Thème, densité, réglages par défaut de la carte et relance du tutoriel.",
  },
];

const FAQ: { q: string; a: string }[] = [
  {
    q: "Le badge « live » ou « mock » en haut à droite, c'est quoi ?",
    a: "Il indique d'où viennent les données affichées. « Live » : elles proviennent de l'API en temps réel. « Mock » : l'API était injoignable, l'application affiche des données de démonstration. Vous pouvez masquer ce badge dans les Paramètres.",
  },
  {
    q: "Quelles zones sont couvertes ?",
    a: "L'application est centrée sur Paris et l'Île-de-France, qui s'affichent par défaut. Vous pouvez élargir à la France entière depuis la carte.",
  },
  {
    q: "Mes critères sont-ils enregistrés ?",
    a: "Vos critères restent actifs pendant votre navigation. Vos préférences d'affichage (thème, densité, réglages de carte) sont, elles, enregistrées sur cet appareil.",
  },
  {
    q: "Pourquoi certaines communes apparaissent en gris ?",
    a: "Le gris signale une donnée manquante pour le mode de couleur sélectionné : la commune n'est pas exclue, l'information n'est simplement pas disponible pour ce critère.",
  },
];

export default function AidePage() {
  const router = useRouter();

  const replayTutorial = () => {
    // The tour starts on the map (its first step lives there).
    router.push("/");
    startOnboarding();
  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-5">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Aide &amp; prise en main</h1>
          <p className="text-sm text-muted">
            Tout pour trouver où acheter à Paris et en Île-de-France avec
            Homepedia.
          </p>
        </div>
        <button
          type="button"
          onClick={replayTutorial}
          className="flex shrink-0 items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-white transition-colors hover:opacity-90"
        >
          <GraduationCap size={15} /> Revoir le tutoriel
        </button>
      </div>

      {/* Le parcours en 3 étapes */}
      <Card className="flex flex-col gap-5">
        <SectionTitle
          icon={Target}
          title="Le parcours en 3 étapes"
          desc="De vos critères à la décision."
        />
        <ol className="flex flex-col gap-4">
          {STEPS.map((s) => (
            <li key={s.n} className="flex gap-3">
              <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-primary-soft text-sm font-semibold text-primary">
                {s.n}
              </span>
              <div>
                <p className="text-sm font-medium">{s.title}</p>
                <p className="text-sm text-muted">{s.desc}</p>
              </div>
            </li>
          ))}
        </ol>
      </Card>

      {/* Définir mes critères */}
      <Card className="flex flex-col gap-5">
        <SectionTitle
          icon={SlidersHorizontal}
          title="Définir mes critères"
          desc="Panneau « Mes critères », à gauche du Cartographe."
        />
        <div className="flex flex-col gap-4">
          {CRITERIA.map((c) => (
            <IconRow key={c.label} icon={c.icon} label={c.label} desc={c.desc} />
          ))}
        </div>
      </Card>

      {/* Le score de matching */}
      <Card className="flex flex-col gap-5">
        <SectionTitle
          icon={Target}
          title="Comment le score est calculé"
          desc="Un score de 0 à 100 par commune, personnalisé selon vos critères."
        />
        <p className="text-sm text-muted">
          Chaque commune est notée sur quatre dimensions, puis combinées selon
          l&apos;importance que vous leur donnez. Plus une dimension a un curseur
          élevé, plus elle pèse dans le score final.
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          {DIMENSIONS.map((d) => (
            <div
              key={d.label}
              className="flex gap-3 rounded-xl border border-line bg-bg/50 p-3"
            >
              <d.icon size={18} className="mt-0.5 shrink-0 text-primary" />
              <div>
                <p className="text-sm font-medium">{d.label}</p>
                <p className="text-xs text-muted">{d.desc}</p>
              </div>
            </div>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          {legendForMode("score").map((item) => (
            <span
              key={item.label}
              className="flex items-center gap-1.5 rounded-lg border border-line bg-card px-2.5 py-1 text-xs text-muted"
            >
              <span
                className="h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: item.color }}
              />
              {item.label}
            </span>
          ))}
        </div>
      </Card>

      {/* Les modes de couleur */}
      <Card className="flex flex-col gap-5">
        <SectionTitle
          icon={Palette}
          title="Lire la carte"
          desc="Changez de mode de couleur pour visualiser un critère à la fois."
        />
        <div className="flex flex-col gap-4">
          {COLOR_MODES.map((mode) => (
            <div key={mode.id} className="flex flex-col gap-2">
              <p className="text-sm font-medium">{mode.label}</p>
              <div className="flex flex-wrap gap-2">
                {legendForMode(mode.id).map((item) => (
                  <span
                    key={item.label}
                    className="flex items-center gap-1.5 rounded-lg border border-line bg-bg/50 px-2.5 py-1 text-xs text-muted"
                  >
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: item.color }}
                    />
                    {item.label}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Les pages */}
      <Card className="flex flex-col gap-5">
        <SectionTitle
          icon={Map}
          title="Les pages de l'application"
          desc="Où trouver quoi."
        />
        <div className="flex flex-col gap-2">
          {PAGES.map((p) => (
            <Link
              key={p.href}
              href={p.href}
              className="flex items-start gap-3 rounded-xl border border-line p-3 transition-colors hover:bg-bg"
            >
              <p.icon size={18} className="mt-0.5 shrink-0 text-primary" />
              <div>
                <p className="text-sm font-medium">{p.label}</p>
                <p className="text-xs text-muted">{p.desc}</p>
              </div>
            </Link>
          ))}
        </div>
      </Card>

      {/* Données */}
      <Card className="flex flex-col gap-3">
        <SectionTitle
          icon={Database}
          title="D'où viennent les données"
          desc="Sources publiques agrégées."
        />
        <p className="text-sm text-muted">
          Homepedia s&apos;appuie sur des données publiques (transactions
          immobilières DVF, INSEE, revenus FiLoSoFi, gares SNCF, équipements BPE),
          agrégées par commune et par arrondissement. Les chiffres reflètent les
          dernières années disponibles et sont fournis à titre indicatif.
        </p>
      </Card>

      {/* FAQ */}
      <Card className="flex flex-col gap-2">
        <SectionTitle title="Questions fréquentes" />
        <div className="flex flex-col divide-y divide-line">
          {FAQ.map((f) => (
            <details key={f.q} className="group py-3">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-sm font-medium">
                {f.q}
                <span className="shrink-0 text-muted transition-transform group-open:rotate-45">
                  +
                </span>
              </summary>
              <p className="mt-2 text-sm text-muted">{f.a}</p>
            </details>
          ))}
        </div>
      </Card>
    </div>
  );
}

function SectionTitle({
  icon: Icon,
  title,
  desc,
}: {
  icon?: LucideIcon;
  title: string;
  desc?: string;
}) {
  return (
    <div className="flex items-start gap-2.5">
      {Icon && <Icon size={18} className="mt-0.5 shrink-0 text-primary" />}
      <div>
        <h2 className="text-base font-semibold">{title}</h2>
        {desc && <p className="text-sm text-muted">{desc}</p>}
      </div>
    </div>
  );
}

function IconRow({
  icon: Icon,
  label,
  desc,
}: {
  icon: LucideIcon;
  label: string;
  desc: string;
}) {
  return (
    <div className="flex gap-3">
      <Icon size={18} className="mt-0.5 shrink-0 text-primary" />
      <div>
        <p className="text-sm font-medium">{label}</p>
        <p className="text-sm text-muted">{desc}</p>
      </div>
    </div>
  );
}
