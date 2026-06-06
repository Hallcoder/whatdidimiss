"use client";

import { AlertCircle, Check, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { SelfAssessmentForm } from "@/components/dashboard/self-assessment-form";
import { useVideoStatus } from "@/lib/hooks/use-video-status";
import { cn } from "@/lib/utils";

const PIPELINE_STEPS = [
  { key: "pending", label: "Queued" },
  { key: "downloading", label: "Downloading video" },
  { key: "uploading_gcs", label: "Uploading to cloud" },
  { key: "analyzing_video", label: "Analyzing video content" },
  { key: "fetching_analytics", label: "Fetching YouTube analytics" },
  { key: "correlating", label: "Correlating engagement data" },
  { key: "synthesizing", label: "Generating AI insights" },
  { key: "completed", label: "Complete" },
];

interface ProcessingStatusProps {
  videoId: string;
  onComplete?: () => void;
}

export function ProcessingStatus({ videoId, onComplete }: ProcessingStatusProps) {
  const { data } = useVideoStatus(videoId);

  const currentStatus = data?.status ?? "pending";
  const isFailed = currentStatus === "failed";
  const isComplete = currentStatus === "completed";

  if (isComplete && onComplete) {
    onComplete();
  }

  const currentIndex = PIPELINE_STEPS.findIndex((s) => s.key === currentStatus);

  return (
  <>
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">
          {isFailed ? "Analysis Failed" : isComplete ? "Analysis Complete" : "Analyzing Your Video"}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <Progress value={data?.progress_pct ?? 0} className="h-2" />

        <div className="space-y-3">
          {PIPELINE_STEPS.map((step, i) => {
            const isDone = i < currentIndex || isComplete;
            const isCurrent = i === currentIndex && !isComplete && !isFailed;

            return (
              <div key={step.key} className="flex items-center gap-3">
                <div
                  className={cn(
                    "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs",
                    isDone && "border-emerald-500 bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
                    isCurrent && "border-blue-500 bg-blue-500/15 text-blue-600 dark:text-blue-400",
                    !isDone && !isCurrent && "border-border text-muted-foreground"
                  )}
                >
                  {isDone ? (
                    <Check className="h-3.5 w-3.5" />
                  ) : isCurrent ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <span className="h-1.5 w-1.5 rounded-full bg-current opacity-30" />
                  )}
                </div>
                <span
                  className={cn(
                    "text-sm",
                    isDone && "text-foreground",
                    isCurrent && "font-medium text-foreground",
                    !isDone && !isCurrent && "text-muted-foreground"
                  )}
                >
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>

        {isFailed && data?.error && (
          <div className="flex items-start gap-2 rounded-lg border border-red-500/20 bg-red-500/10 p-3">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
            <p className="text-sm text-red-600 dark:text-red-400">{data.error}</p>
          </div>
        )}
      </CardContent>
    </Card>

    {!isComplete && !isFailed && (
      <SelfAssessmentForm videoId={videoId} />
    )}
  </>
  );
}
