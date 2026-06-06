"use client";

import { use } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useAnalysis } from "@/lib/hooks/use-analysis";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatMs } from "@/lib/utils/format";

export default function AnalysisPage({
  params,
}: {
  params: Promise<{ videoId: string }>;
}) {
  const { videoId } = use(params);
  const { data, isLoading } = useAnalysis(videoId);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
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

      <h1 className="text-2xl font-bold">Video Analysis</h1>

      {data && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <Card>
              <CardContent className="pt-5">
                <p className="text-xs text-muted-foreground">Shot Count</p>
                <p className="text-2xl font-bold">{data.shot_count}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-5">
                <p className="text-xs text-muted-foreground">Avg Pacing</p>
                <p className="text-2xl font-bold">{data.avg_pacing} shots/min</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-5">
                <p className="text-xs text-muted-foreground">Transcript</p>
                <p className="text-2xl font-bold">{data.transcript_available ? "Available" : "N/A"}</p>
              </CardContent>
            </Card>
          </div>

          {data.detected_labels.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Detected Labels</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {data.detected_labels.map((label) => (
                    <Badge key={label} variant="outline">{label}</Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {data.segments.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Segments</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {data.segments.map((seg) => (
                    <div
                      key={seg.id}
                      className="flex items-center gap-3 rounded-md border px-3 py-2 text-sm"
                    >
                      <span className="font-mono text-xs text-muted-foreground">
                        {formatMs(seg.start_ms)} – {formatMs(seg.end_ms)}
                      </span>
                      <Badge variant="outline" className="text-[10px]">
                        {seg.segment_type ?? "unknown"}
                      </Badge>
                      {seg.pacing_score != null && (
                        <span className="text-xs text-muted-foreground">
                          {seg.pacing_score} shots/min
                        </span>
                      )}
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
