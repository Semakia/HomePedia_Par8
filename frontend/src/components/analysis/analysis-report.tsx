import {
  Wallet,
  Euro,
  TrainFront,
  Store,
  Users,
  LineChart,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import type { Analysis, InsightCategory, InsightTone } from "@/lib/analysis";

// Renders the rule-based textual analysis: a lead synthesis paragraph + one
// card per thematic insight. Pure presentation (no hooks) — safe as a Server
// Component.

const ICON: Record<InsightCategory, LucideIcon> = {
  affordability: Wallet,
  market: Euro,
  transport: TrainFront,
  amenities: Store,
  demographics: Users,
  trend: LineChart,
};

const TONE: Record<InsightTone, { dot: string; text: string; ring: string }> = {
  positive: { dot: "bg-emerald-500", text: "text-emerald-700", ring: "ring-emerald-200" },
  neutral: { dot: "bg-slate-400", text: "text-slate-600", ring: "ring-slate-200" },
  warning: { dot: "bg-amber-500", text: "text-amber-700", ring: "ring-amber-200" },
};

export function AnalysisReport({ analysis }: { analysis: Analysis }) {
  return (
    <div className="flex flex-col gap-6">
      {/* Lead synthesis */}
      <Card className="bg-primary-soft/40">
        <div className="flex items-start gap-3">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-primary text-white">
            <Sparkles size={18} />
          </span>
          <div>
            <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-primary">
              Synthèse
            </p>
            <p className="text-[15px] leading-relaxed text-ink">{analysis.summary}</p>
          </div>
        </div>
      </Card>

      {/* Thematic insights */}
      {analysis.insights.length > 0 && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {analysis.insights.map((ins) => {
            const Icon = ICON[ins.category];
            const tone = TONE[ins.tone];
            return (
              <Card key={ins.category} className="flex items-start gap-3 p-5">
                <span
                  className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-bg ring-1 ${tone.ring} ${tone.text}`}
                >
                  <Icon size={17} />
                </span>
                <div className="min-w-0">
                  <p className="mb-0.5 flex items-center gap-2 text-sm font-semibold">
                    {ins.title}
                    <span className={`h-1.5 w-1.5 rounded-full ${tone.dot}`} />
                  </p>
                  <p className="text-sm leading-relaxed text-muted">{ins.body}</p>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
