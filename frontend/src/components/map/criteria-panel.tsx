"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { RotateCcw, SlidersHorizontal } from "lucide-react";
import {
  DESSERTE_LEVELS,
  EQUIPEMENT_LEVELS,
  targetPricePerM2,
  type Criteria,
  type Weights,
} from "@/lib/scoring";

const WEIGHT_LABELS: { key: keyof Weights; label: string; hint: string }[] = [
  { key: "budget", label: "Budget", hint: "Prix accessible pour mon enveloppe" },
  { key: "transport", label: "Transport", hint: "Proximité et qualité du rail" },
  { key: "services", label: "Services", hint: "Commerces, santé, écoles" },
  { key: "jeune", label: "Ambiance jeune", hint: "Part d'actifs et de jeunes" },
];

const fieldCls =
  "w-full rounded-xl border border-line bg-bg/60 px-3 py-2 text-sm outline-none focus:border-primary/40";

const NBSP = " "; // narrow no-break space — fr-FR thousands grouping
const group = (digits: string) =>
  digits.replace(/\B(?=(\d{3})+(?!\d))/g, NBSP);

/** Number (model) -> grouped French display string. null/empty -> "". */
function formatNum(n: number | null, allowDecimal: boolean): string {
  if (n == null) return "";
  const [int, frac = ""] = String(allowDecimal ? n : Math.trunc(n)).split(".");
  const sign = int.startsWith("-") ? "-" : "";
  const display = sign + group(int.replace("-", ""));
  return frac ? `${display},${frac}` : display;
}

/**
 * Parses a raw input into both the grouped display string (so formatting is
 * live) and the numeric model value. Keeps a trailing decimal separator the
 * user just typed, so "45," round-trips instead of snapping back to "45".
 */
function normalizeNum(
  raw: string,
  allowDecimal: boolean,
): { display: string; value: number | null } {
  let intPart = "";
  let fracPart = "";
  let seenDot = false;
  for (const ch of raw) {
    if (ch >= "0" && ch <= "9") {
      if (seenDot) fracPart += ch;
      else intPart += ch;
    } else if (allowDecimal && (ch === "." || ch === ",") && !seenDot) {
      seenDot = true;
    }
  }
  if (fracPart.length > 2) fracPart = fracPart.slice(0, 2);
  if (intPart === "" && !seenDot) return { display: "", value: null };

  const intGroup = group(intPart) || (seenDot ? "0" : "");
  const display = seenDot ? `${intGroup},${fracPart}` : intGroup;
  const value = Number(`${intPart || "0"}${seenDot ? `.${fracPart || "0"}` : ""}`);
  return { display, value };
}

/**
 * Controlled numeric field with live French thousands grouping. Holds the
 * display string locally (so the caret can be restored after each reformat)
 * while emitting the parsed number to the parent.
 */
function NumberInput({
  value,
  onChange,
  allowDecimal = false,
  className,
  placeholder,
}: {
  value: number | null;
  onChange: (n: number | null) => void;
  allowDecimal?: boolean;
  className?: string;
  placeholder?: string;
}) {
  const ref = useRef<HTMLInputElement>(null);
  const focused = useRef(false);
  const caret = useRef<number | null>(null);
  const [text, setText] = useState(() => formatNum(value, allowDecimal));

  // Significant chars (digits + decimal separator) — group spaces don't count.
  const isSig = (ch: string) => /\d/.test(ch) || (allowDecimal && /[.,]/.test(ch));

  // Reflect external changes (e.g. the Reset button) only while not editing,
  // so we never fight the user's caret.
  useEffect(() => {
    if (!focused.current) setText(formatNum(value, allowDecimal));
  }, [value, allowDecimal]);

  // After a live reformat, place the caret back after the same number of
  // significant chars it preceded, so mid-string edits don't jump to the end.
  useLayoutEffect(() => {
    const el = ref.current;
    if (caret.current == null || !el) return;
    const want = caret.current;
    caret.current = null;
    let seen = 0;
    let pos = el.value.length;
    for (let i = 0; i < el.value.length; i++) {
      if (isSig(el.value[i])) {
        if (seen === want) {
          pos = i;
          break;
        }
        seen++;
      }
    }
    el.setSelectionRange(pos, pos);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, allowDecimal]);

  return (
    <input
      ref={ref}
      type="text"
      inputMode={allowDecimal ? "decimal" : "numeric"}
      value={text}
      placeholder={placeholder}
      className={className}
      onFocus={() => {
        focused.current = true;
      }}
      onBlur={() => {
        focused.current = false;
        setText(formatNum(value, allowDecimal)); // canonicalize (drop trailing ",")
      }}
      onChange={(e) => {
        const raw = e.target.value;
        const sel = e.target.selectionStart ?? raw.length;
        let sig = 0;
        for (let i = 0; i < sel; i++) if (isSig(raw[i])) sig++;
        caret.current = sig;

        const { display, value: parsed } = normalizeNum(raw, allowDecimal);
        setText(display);
        onChange(parsed);
      }}
    />
  );
}

export function CriteriaPanel({
  criteria,
  weights,
  onCriteria,
  onWeights,
  onReset,
}: {
  criteria: Criteria;
  weights: Weights;
  onCriteria: (next: Criteria) => void;
  onWeights: (next: Weights) => void;
  onReset: () => void;
}) {
  const setC = (patch: Partial<Criteria>) => onCriteria({ ...criteria, ...patch });
  const setW = (patch: Partial<Weights>) => onWeights({ ...weights, ...patch });
  const target = targetPricePerM2(criteria);

  return (
    <div className="flex flex-col gap-5" data-tour="criteria">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          <SlidersHorizontal size={16} className="text-primary" />
          Mes critères
        </h2>
        <button
          type="button"
          onClick={onReset}
          className="flex items-center gap-1 rounded-lg border border-line px-2 py-1 text-xs text-muted hover:bg-bg"
        >
          <RotateCcw size={13} />
          Réinitialiser
        </button>
      </div>

      {/* Budget + surface -> target €/m² */}
      <div className="flex flex-col gap-3">
        <Field label="Budget total">
          <div className="relative">
            <NumberInput
              value={criteria.budgetTotal}
              onChange={(n) => setC({ budgetTotal: n })}
              placeholder="ex. 350 000"
              className={`${fieldCls} pr-8`}
            />
            <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted">
              €
            </span>
          </div>
        </Field>
        <Field label="Surface souhaitée">
          <div className="relative">
            <NumberInput
              value={criteria.surface}
              onChange={(n) => setC({ surface: n })}
              allowDecimal
              placeholder="ex. 45"
              className={`${fieldCls} pr-10`}
            />
            <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted">
              m²
            </span>
          </div>
        </Field>
        {target != null && (
          <p className="rounded-lg bg-primary-soft px-3 py-2 text-xs text-primary">
            Cible : <b>{Math.round(target).toLocaleString("fr-FR")} €/m²</b> — les
            communes sous ce prix sont privilégiées.
          </p>
        )}
      </div>

      <Divider />

      {/* Hard filters */}
      <div className="flex flex-col gap-3">
        <Field label="Desserte transport minimale">
          <select
            value={criteria.desserteMin}
            onChange={(e) => setC({ desserteMin: e.target.value as Criteria["desserteMin"] })}
            className={fieldCls}
          >
            <option value="">Indifférent</option>
            {[...DESSERTE_LEVELS].reverse().map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Distance max à une gare">
          <div className="relative">
            <input
              type="number"
              inputMode="numeric"
              min={0}
              step={0.5}
              value={criteria.distanceGareMax ?? ""}
              onChange={(e) =>
                setC({ distanceGareMax: e.target.value === "" ? null : Number(e.target.value) })
              }
              placeholder="indifférent"
              className={`${fieldCls} pr-10`}
            />
            <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted">
              km
            </span>
          </div>
        </Field>
        <Field label="Niveau d'équipement minimal">
          <select
            value={criteria.equipementMin}
            onChange={(e) => setC({ equipementMin: e.target.value as Criteria["equipementMin"] })}
            className={fieldCls}
          >
            <option value="">Indifférent</option>
            {[...EQUIPEMENT_LEVELS].reverse().map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <Divider />

      {/* Weight sliders */}
      <div className="flex flex-col gap-4">
        <p className="text-xs font-medium text-muted">Ce qui compte le plus pour moi</p>
        {WEIGHT_LABELS.map(({ key, label, hint }) => (
          <div key={key} className="flex flex-col gap-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-ink">{label}</span>
              <span className="tabular-nums text-muted">{weights[key]}</span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={weights[key]}
              onChange={(e) => setW({ [key]: Number(e.target.value) } as Partial<Weights>)}
              className="accent-primary"
            />
            <span className="text-[11px] text-muted/80">{hint}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-medium text-muted">{label}</span>
      {children}
    </label>
  );
}

function Divider() {
  return <div className="h-px bg-line" />;
}
