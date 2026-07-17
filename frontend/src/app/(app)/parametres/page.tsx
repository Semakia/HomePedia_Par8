"use client";

import { Monitor, Moon, Sun, GraduationCap } from "lucide-react";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/card";
import { usePreferences } from "@/components/preferences-provider";
import { start as startOnboarding } from "@/components/onboarding/onboarding-provider";
import { COLOR_MODES } from "@/lib/map-modes";
import type { Density, Theme } from "@/lib/preferences";

const THEME_OPTIONS: { id: Theme; label: string; icon: typeof Sun }[] = [
  { id: "light", label: "Clair", icon: Sun },
  { id: "dark", label: "Sombre", icon: Moon },
  { id: "system", label: "Système", icon: Monitor },
];

const DENSITY_OPTIONS: { id: Density; label: string }[] = [
  { id: "comfortable", label: "Confortable" },
  { id: "compact", label: "Compact" },
];

export default function ParametresPage() {
  const { prefs, setPrefs } = usePreferences();
  const router = useRouter();

  const replayTutorial = () => {
    // The tour starts on the map (its first step lives there).
    router.push("/");
    startOnboarding();
  };

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-5">
      <div>
        <h1 className="text-xl font-semibold">Paramètres</h1>
        <p className="text-sm text-muted">
          Personnalisez l&apos;apparence et le comportement de l&apos;application.
          Vos choix sont enregistrés sur cet appareil.
        </p>
      </div>

      {/* Apparence */}
      <Card className="flex flex-col gap-5">
        <SectionTitle
          title="Apparence"
          desc="Thème et densité de l'interface."
        />

        <Field label="Thème" desc="Le mode Système suit les réglages de votre OS.">
          <div className="flex flex-wrap gap-2">
            {THEME_OPTIONS.map((opt) => {
              const Icon = opt.icon;
              return (
                <Segment
                  key={opt.id}
                  active={prefs.theme === opt.id}
                  onClick={() => setPrefs({ theme: opt.id })}
                >
                  <Icon size={15} /> {opt.label}
                </Segment>
              );
            })}
          </div>
        </Field>

        <Field label="Densité" desc="Compact resserre les espacements et le texte.">
          <div className="flex flex-wrap gap-2">
            {DENSITY_OPTIONS.map((opt) => (
              <Segment
                key={opt.id}
                active={prefs.density === opt.id}
                onClick={() => setPrefs({ density: opt.id })}
              >
                {opt.label}
              </Segment>
            ))}
          </div>
        </Field>
      </Card>

      {/* Interface */}
      <Card className="flex flex-col gap-5">
        <SectionTitle title="Interface" desc="Éléments affichés à l'écran." />

        <ToggleRow
          label="Badge de source de données"
          desc="Affiche l'indicateur live / mock en haut à droite."
          checked={prefs.showBadge}
          onChange={(v) => setPrefs({ showBadge: v })}
        />
      </Card>

      {/* Carte */}
      <Card className="flex flex-col gap-5">
        <SectionTitle
          title="Carte"
          desc="Réglages par défaut du Cartographe."
        />

        <Field
          label="Critère de coloration par défaut"
          desc="Mode de couleur appliqué à l'ouverture de la carte."
        >
          <select
            value={prefs.mapColorMode}
            onChange={(e) =>
              setPrefs({ mapColorMode: e.target.value as typeof prefs.mapColorMode })
            }
            className="w-full rounded-lg border border-line bg-card px-3 py-2 text-sm text-ink focus:border-primary focus:outline-none"
          >
            {COLOR_MODES.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
        </Field>

        <ToggleRow
          label="Afficher les gares par défaut"
          desc="Active le calque des gares dès l'ouverture de la carte."
          checked={prefs.mapShowGares}
          onChange={(v) => setPrefs({ mapShowGares: v })}
        />
      </Card>

      {/* Aide */}
      <Card className="flex flex-col gap-5">
        <SectionTitle
          title="Aide"
          desc="Revoir la prise en main de l'application."
        />

        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium">Tutoriel de démarrage</p>
            <p className="text-xs text-muted">
              Relance la visite guidée du parcours (critères → ville → statistiques).
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
      </Card>
    </div>
  );
}

function SectionTitle({ title, desc }: { title: string; desc: string }) {
  return (
    <div>
      <h2 className="text-base font-semibold">{title}</h2>
      <p className="text-sm text-muted">{desc}</p>
    </div>
  );
}

function Field({
  label,
  desc,
  children,
}: {
  label: string;
  desc?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2">
      <div>
        <p className="text-sm font-medium">{label}</p>
        {desc && <p className="text-xs text-muted">{desc}</p>}
      </div>
      {children}
    </div>
  );
}

function Segment({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
        active
          ? "bg-primary text-white"
          : "border border-line bg-card text-muted hover:bg-bg hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}

function ToggleRow({
  label,
  desc,
  checked,
  onChange,
}: {
  label: string;
  desc?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <p className="text-sm font-medium">{label}</p>
        {desc && <p className="text-xs text-muted">{desc}</p>}
      </div>
      {/* No transition on the track colour: it interpolates between two
          var()-based tokens, and a hydration-time colour change (the SSR
          default differs from the stored value) leaves Chrome's computed value
          stuck on the start colour. Switching instantly avoids that bug. */}
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        onClick={() => onChange(!checked)}
        className={`flex h-6 w-11 shrink-0 items-center rounded-full px-0.5 ${
          checked ? "justify-end bg-primary" : "justify-start bg-line"
        }`}
      >
        <span className="h-5 w-5 rounded-full bg-white shadow-sm" />
      </button>
    </div>
  );
}
