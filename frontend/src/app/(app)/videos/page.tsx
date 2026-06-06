"use client";

import Link from "next/link";
import { Plus, RefreshCw, Trash2, Tv } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { StatusBadge } from "@/components/videos/status-badge";
import { useDeleteVideo, useReanalyzeVideo, useVideos } from "@/lib/hooks/use-videos";
import { formatDuration, timeAgo } from "@/lib/utils/format";

export default function VideosPage() {
  const { data, isLoading } = useVideos();
  const deleteMutation = useDeleteVideo();
  const reanalyzeMutation = useReanalyzeVideo();

  function handleDelete(videoId: string, title: string | null) {
    if (!confirm(`Delete "${title ?? "Untitled"}"?`)) return;
    deleteMutation.mutate(videoId, {
      onSuccess: () => toast.success("Video deleted"),
      onError: () => toast.error("Failed to delete video"),
    });
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Videos</h1>
          <p className="text-sm text-muted-foreground">
            Your analyzed videos and their coaching insights.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" render={<Link href="/videos/browse" />}>
            <Tv className="mr-2 h-4 w-4" />
            Browse Channel
          </Button>
          <Button render={<Link href="/videos/analyze" />}>
            <Plus className="mr-2 h-4 w-4" />
            Analyze Video
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : !data?.items.length ? (
        <div className="rounded-lg border border-dashed border-border p-12 text-center">
          <p className="text-muted-foreground">No videos analyzed yet.</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Submit a YouTube URL to get started.
          </p>
        </div>
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-16" />
                <TableHead>Title</TableHead>
                <TableHead className="w-20 text-center">Score</TableHead>
                <TableHead className="w-32">Status</TableHead>
                <TableHead className="w-24">Duration</TableHead>
                <TableHead className="w-32 text-right">Added</TableHead>
                <TableHead className="w-12" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((video) => (
                <TableRow key={video.id} className="group">
                  <TableCell>
                    {video.thumbnail_url ? (
                      <img
                        src={video.thumbnail_url}
                        alt=""
                        className="h-10 w-16 rounded object-cover"
                      />
                    ) : (
                      <div className="h-10 w-16 rounded bg-muted" />
                    )}
                  </TableCell>
                  <TableCell>
                    <Link
                      href={`/dashboard/${video.id}`}
                      className="font-medium hover:underline"
                    >
                      {video.title ?? "Untitled"}
                    </Link>
                  </TableCell>
                  <TableCell className="text-center">
                    <VideoScoreBadge score={video.video_score} />
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={video.processing_status} />
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDuration(video.duration_seconds)}
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground">
                    {timeAgo(video.created_at)}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100">
                      {(video.processing_status === "completed" || video.processing_status === "failed") && (
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Re-analyze"
                          onClick={() =>
                            reanalyzeMutation.mutate(video.id, {
                              onSuccess: () => toast.success("Re-analysis started"),
                              onError: () => toast.error("Failed to start re-analysis"),
                            })
                          }
                          disabled={reanalyzeMutation.isPending}
                        >
                          <RefreshCw className="h-4 w-4 text-muted-foreground hover:text-foreground" />
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDelete(video.id, video.title)}
                        disabled={deleteMutation.isPending}
                      >
                        <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

function VideoScoreBadge({ score }: { score: number | null }) {
  if (score == null) return <span className="text-xs text-muted-foreground">--</span>;

  const color =
    score >= 70
      ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400"
      : score >= 50
        ? "bg-amber-500/15 text-amber-700 dark:text-amber-400"
        : "bg-red-500/15 text-red-700 dark:text-red-400";

  return (
    <span
      className={`inline-flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold ${color}`}
    >
      {score}
    </span>
  );
}
