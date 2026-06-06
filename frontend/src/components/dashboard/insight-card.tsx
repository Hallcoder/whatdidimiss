import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { InsightSummary } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const variantStyles: Record<string, string> = {
  win: "border-l-emerald-500",
  improvement: "border-l-amber-500",
  next_post: "border-l-blue-500",
  creative_tweak: "border-l-purple-500",
};

const categoryColors: Record<string, string> = {
  hook: "bg-orange-500/15 text-orange-600 dark:text-orange-400",
  pacing: "bg-sky-500/15 text-sky-600 dark:text-sky-400",
  content: "bg-indigo-500/15 text-indigo-600 dark:text-indigo-400",
  cta: "bg-rose-500/15 text-rose-600 dark:text-rose-400",
  visual: "bg-violet-500/15 text-violet-600 dark:text-violet-400",
  audio: "bg-teal-500/15 text-teal-600 dark:text-teal-400",
  topic: "bg-cyan-500/15 text-cyan-600 dark:text-cyan-400",
  engagement: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
  thumbnail: "bg-pink-500/15 text-pink-600 dark:text-pink-400",
  title: "bg-yellow-500/15 text-yellow-600 dark:text-yellow-400",
};

const creatorMatchConfig: Record<string, { label: string; className: string }> = {
  predicted: {
    label: "You called it",
    className: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30",
  },
  blind_spot: {
    label: "Blind spot",
    className: "bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30",
  },
  over_critical: {
    label: "Too harsh on yourself",
    className: "bg-blue-500/15 text-blue-700 dark:text-blue-400 border-blue-500/30",
  },
  under_critical: {
    label: "Overconfident",
    className: "bg-red-500/15 text-red-700 dark:text-red-400 border-red-500/30",
  },
};

interface InsightCardProps {
  insight: InsightSummary;
  variant?: string;
}

export function InsightCard({ insight, variant }: InsightCardProps) {
  const type = variant ?? insight.type;
  const borderClass = variantStyles[type] ?? "border-l-zinc-500";
  const matchConfig = insight.creator_match ? creatorMatchConfig[insight.creator_match] : null;

  return (
    <Card className={cn("border-l-4", borderClass)}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-sm font-semibold leading-tight">
            {insight.title}
          </CardTitle>
          {insight.category && (
            <Badge
              variant="outline"
              className={cn(
                "shrink-0 text-[10px]",
                categoryColors[insight.category] ?? "bg-zinc-500/15 text-zinc-500"
              )}
            >
              {insight.category}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm leading-relaxed text-muted-foreground">
          {insight.description}
        </p>
        {matchConfig && (
          <div className="mt-2">
            <Badge variant="outline" className={cn("text-[10px]", matchConfig.className)}>
              {matchConfig.label}
            </Badge>
            {insight.creator_match_note && (
              <p className="mt-1 text-[10px] italic text-muted-foreground">
                {insight.creator_match_note}
              </p>
            )}
          </div>
        )}
        {insight.confidence != null && (
          <div className="mt-3 flex items-center gap-2">
            <div className="h-1 flex-1 rounded-full bg-muted">
              <div
                className="h-1 rounded-full bg-foreground/30"
                style={{ width: `${insight.confidence * 100}%` }}
              />
            </div>
            <span className="text-[10px] text-muted-foreground">
              {Math.round(insight.confidence * 100)}%
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
