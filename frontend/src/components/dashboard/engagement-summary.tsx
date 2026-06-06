import { BarChart3, Clock, Eye, TrendingDown, TrendingUp } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { EngagementSummary as EngagementSummaryType } from "@/lib/api/types";
import { formatMs, formatNumber, formatPercent } from "@/lib/utils/format";

interface EngagementSummaryCardsProps {
  data: EngagementSummaryType;
}

export function EngagementSummaryCards({ data }: EngagementSummaryCardsProps) {
  const cards = [
    {
      label: "Views",
      value: formatNumber(data.views),
      icon: Eye,
    },
    {
      label: "Avg. Retention",
      value: formatPercent(data.avg_retention_pct),
      icon: BarChart3,
    },
    {
      label: "Best Segment",
      value: data.best_segment
        ? `${formatMs(data.best_segment.start_ms)} – ${formatMs(data.best_segment.end_ms)}`
        : "—",
      sub: data.best_segment ? formatPercent(data.best_segment.avg_retention ? data.best_segment.avg_retention * 100 : null) : undefined,
      icon: TrendingUp,
    },
    {
      label: "Worst Segment",
      value: data.worst_segment
        ? `${formatMs(data.worst_segment.start_ms)} – ${formatMs(data.worst_segment.end_ms)}`
        : "—",
      sub: data.worst_segment ? formatPercent(data.worst_segment.avg_retention ? data.worst_segment.avg_retention * 100 : null) : undefined,
      icon: TrendingDown,
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <Card key={card.label}>
          <CardContent className="flex items-start gap-3 pt-5">
            <div className="rounded-md bg-muted p-2">
              <card.icon className="h-4 w-4 text-muted-foreground" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">{card.label}</p>
              <p className="text-lg font-semibold">{card.value}</p>
              {card.sub && <p className="text-xs text-muted-foreground">{card.sub} retention</p>}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
