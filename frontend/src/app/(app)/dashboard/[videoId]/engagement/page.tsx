"use client";

import { use } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { RetentionCurveChart } from "@/components/charts/retention-curve-chart";
import { useEngagement } from "@/lib/hooks/use-engagement";
import { formatNumber, formatPercent } from "@/lib/utils/format";

export default function EngagementPage({
  params,
}: {
  params: Promise<{ videoId: string }>;
}) {
  const { videoId } = use(params);
  const { data, isLoading } = useEngagement(videoId);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Link
        href={`/dashboard/${videoId}`}
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Dashboard
      </Link>

      <h1 className="text-2xl font-bold">Engagement Details</h1>

      {data && (
        <>
          <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
            {[
              { label: "Views", value: formatNumber(data.overview.views) },
              { label: "Likes", value: formatNumber(data.overview.likes) },
              { label: "Comments", value: formatNumber(data.overview.comments) },
              { label: "Shares", value: formatNumber(data.overview.shares) },
              { label: "Avg Duration", value: data.overview.avg_view_duration_seconds ? `${Math.round(data.overview.avg_view_duration_seconds)}s` : "—" },
              { label: "Avg View %", value: formatPercent(data.overview.avg_view_percentage) },
            ].map((stat) => (
              <Card key={stat.label}>
                <CardContent className="pt-5">
                  <p className="text-xs text-muted-foreground">{stat.label}</p>
                  <p className="text-lg font-semibold">{stat.value}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          {data.retention_curve.length > 0 && (
            <RetentionCurveChart data={data.retention_curve} height={350} />
          )}

          {data.traffic_sources && Object.keys(data.traffic_sources).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Traffic Sources</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(data.traffic_sources)
                    .sort(([, a], [, b]) => b - a)
                    .map(([source, pct]) => (
                      <div key={source} className="flex items-center gap-3">
                        <span className="w-40 truncate text-sm">{source}</span>
                        <div className="h-2 flex-1 rounded-full bg-muted">
                          <div
                            className="h-2 rounded-full bg-blue-500"
                            style={{ width: `${Math.min(pct, 100)}%` }}
                          />
                        </div>
                        <span className="w-12 text-right text-xs text-muted-foreground">
                          {pct.toFixed(1)}%
                        </span>
                      </div>
                    ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
