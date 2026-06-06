"use client";

import { use } from "react";
import Link from "next/link";
import { ArrowLeft, BarChart3, Brain, FileText, LineChart, Mic, Palette, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { RetentionCurveChart } from "@/components/charts/retention-curve-chart";
import { AnalysisSection } from "@/components/dashboard/analysis-section";
import { AudienceInsights } from "@/components/dashboard/audience-insights";
import { EngagementSummaryCards } from "@/components/dashboard/engagement-summary";
import { InsightCard } from "@/components/dashboard/insight-card";
import { ProcessingStatus } from "@/components/dashboard/processing-status";
import { VideoHeader } from "@/components/dashboard/video-header";
import { cn } from "@/lib/utils";
import { useDashboard } from "@/lib/hooks/use-dashboard";
import { useEngagement } from "@/lib/hooks/use-engagement";
import { useReanalyzeVideo } from "@/lib/hooks/use-videos";

export default function DashboardPage({
  params,
}: {
  params: Promise<{ videoId: string }>;
}) {
  const { videoId } = use(params);
  const { data, isLoading, isError, refetch } = useDashboard(videoId);
  const { data: engagement } = useEngagement(videoId);
  const reanalyzeMutation = useReanalyzeVideo();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-20 w-full" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <ErrorState
        title="Dashboard unavailable"
        message="Could not load dashboard data for this video."
        onRetry={() => refetch()}
      />
    );
  }

  const isProcessing = data.processing_status !== "completed" && data.processing_status !== "failed";
  const d = data as unknown as Record<string, unknown>;

  return (
    <div className="space-y-8">
      <Link
        href="/videos"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Videos
      </Link>

      <VideoHeader
        title={data.video.title}
        youtubeVideoId={data.video.youtube_video_id}
        thumbnailUrl={data.video.thumbnail_url}
        durationSeconds={data.video.duration_seconds}
        videoScore={data.video.video_score}
      />

      {isProcessing ? (
        <ProcessingStatus videoId={videoId} onComplete={() => refetch()} />
      ) : (
        <>
          <EngagementSummaryCards data={data.engagement_summary} />

          {engagement?.retention_curve && engagement.retention_curve.length > 0 && (
            <RetentionCurveChart data={engagement.retention_curve} />
          )}

          {/* Top Wins */}
          {data.top_wins.length > 0 && (
            <section>
              <h2 className="mb-3 text-lg font-semibold">Top Wins</h2>
              <div className="grid gap-3 md:grid-cols-3">
                {data.top_wins.map((insight) => (
                  <InsightCard key={insight.id} insight={insight} variant="win" />
                ))}
              </div>
            </section>
          )}

          {/* Top Improvements */}
          {data.top_improvements.length > 0 && (
            <section>
              <h2 className="mb-3 text-lg font-semibold">Top Improvements</h2>
              <div className="grid gap-3 md:grid-cols-3">
                {data.top_improvements.map((insight) => (
                  <InsightCard key={insight.id} insight={insight} variant="improvement" />
                ))}
              </div>
            </section>
          )}

          {/* Script Analysis */}
          {d.script_analysis && (
            <AnalysisSection
              title="Script Analysis"
              icon={<FileText className="h-4 w-4" />}
              data={d.script_analysis as Record<string, unknown>}
              scoreFields={[
                { key: "hook", label: "Hook" },
                { key: "structure", label: "Structure" },
                { key: "clarity", label: "Clarity" },
                { key: "cta", label: "Call to Action" },
              ]}
              textFields={[
                { key: "rewritten_hook", label: "Suggested Hook (ready to use)" },
                { key: "rewritten_cta", label: "Suggested CTA (ready to use)" },
              ]}
            />
          )}

          {/* Delivery Analysis */}
          {d.delivery_analysis && (
            <AnalysisSection
              title="Delivery Analysis"
              icon={<Mic className="h-4 w-4" />}
              data={d.delivery_analysis as Record<string, unknown>}
              scoreFields={[
                { key: "energy", label: "Energy" },
                { key: "pacing", label: "Pacing" },
                { key: "personality", label: "Personality" },
              ]}
              textFields={[
                { key: "filler_words", label: "Filler Words Detected" },
              ]}
            />
          )}

          {/* Visual Analysis */}
          {d.visual_analysis && (
            <AnalysisSection
              title="Visual Analysis"
              icon={<Palette className="h-4 w-4" />}
              data={d.visual_analysis as Record<string, unknown>}
              scoreFields={[
                { key: "composition", label: "Composition" },
                { key: "broll", label: "B-Roll Usage" },
                { key: "text_overlay", label: "Text Overlays" },
              ]}
              textFields={[
                { key: "thumbnail_suggestions", label: "Thumbnail Suggestions" },
              ]}
            />
          )}

          {/* Audience Insights */}
          {d.audience_insights && (
            <AudienceInsights data={d.audience_insights as Record<string, unknown>} />
          )}

          {/* Next Post Ideas */}
          {data.next_post_ideas.length > 0 && (
            <section>
              <h2 className="mb-3 text-lg font-semibold">Next Post Ideas</h2>
              <div className="grid gap-3 md:grid-cols-2">
                {data.next_post_ideas.map((insight) => (
                  <InsightCard key={insight.id} insight={insight} variant="next_post" />
                ))}
              </div>
            </section>
          )}

          {/* Creative Tweaks */}
          {data.creative_tweaks.length > 0 && (
            <section>
              <h2 className="mb-3 text-lg font-semibold">Quick Fixes (5-min tweaks)</h2>
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {data.creative_tweaks.map((insight) => (
                  <InsightCard key={insight.id} insight={insight} variant="creative_tweak" />
                ))}
              </div>
            </section>
          )}

          {/* Deep-dive links */}
          <div className="flex flex-wrap gap-3 pt-2">
            <Button variant="outline" render={<Link href={`/dashboard/${videoId}/analysis`} />}>
              <Brain className="mr-2 h-4 w-4" />
              Video Analysis
            </Button>
            <Button variant="outline" render={<Link href={`/dashboard/${videoId}/engagement`} />}>
              <LineChart className="mr-2 h-4 w-4" />
              Engagement Details
            </Button>
            <Button variant="outline" render={<Link href={`/dashboard/${videoId}/insights`} />}>
              <BarChart3 className="mr-2 h-4 w-4" />
              All Insights
            </Button>
            <Button
              variant="outline"
              disabled={reanalyzeMutation.isPending}
              onClick={() =>
                reanalyzeMutation.mutate(videoId, {
                  onSuccess: () => {
                    toast.success("Re-analysis started");
                    refetch();
                  },
                  onError: () => toast.error("Failed to start re-analysis"),
                })
              }
            >
              <RefreshCw className={cn("mr-2 h-4 w-4", reanalyzeMutation.isPending && "animate-spin")} />
              Re-analyze
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
