"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Link2, Loader2, PlayCircle } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/components/providers/auth-provider";
import { getGoogleLoginUrl } from "@/lib/api/auth";
import { useAnalyzeVideo, useChannelVideos } from "@/lib/hooks/use-videos";
import { formatDuration, formatNumber, timeAgo } from "@/lib/utils/format";

export default function BrowseChannelPage() {
  const router = useRouter();
  const { user } = useAuth();
  const hasChannel = !!user?.channel;
  const { data, isLoading, isError, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useChannelVideos();
  const analyzeMutation = useAnalyzeVideo();
  const [isConnecting, setIsConnecting] = useState(false);

  if (!hasChannel) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Link
            href="/videos"
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <h1 className="text-2xl font-bold">Browse Channel</h1>
        </div>
        <div className="rounded-lg border border-dashed border-border p-12 text-center">
          <Link2 className="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
          <p className="font-medium">No YouTube channel connected</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Connect your YouTube channel to browse and analyze your videos with full analytics data.
          </p>
          <Button
            className="mt-4"
            onClick={async () => {
              setIsConnecting(true);
              try {
                const { auth_url } = await getGoogleLoginUrl();
                window.location.href = auth_url;
              } catch {
                toast.error("Failed to start channel connection");
                setIsConnecting(false);
              }
            }}
            disabled={isConnecting}
          >
            {isConnecting ? "Connecting..." : "Connect YouTube Channel"}
          </Button>
        </div>
      </div>
    );
  }

  const allVideos = data?.pages.flatMap((page) => page.items) ?? [];

  function handleAnalyze(youtubeVideoId: string) {
    const url = `https://www.youtube.com/watch?v=${youtubeVideoId}`;
    analyzeMutation.mutate(url, {
      onSuccess: (res) => {
        toast.success("Video submitted for analysis");
        router.push(`/dashboard/${res.video_id}`);
      },
      onError: (err: unknown) => {
        const msg =
          (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data
            ?.error?.message ?? "Failed to start analysis.";
        toast.error(msg);
      },
    });
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/videos"
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold">Browse Channel</h1>
            <p className="text-sm text-muted-foreground">
              Pick a video from your YouTube channel to analyze.
            </p>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-64 w-full rounded-lg" />
          ))}
        </div>
      ) : isError ? (
        <div className="rounded-lg border border-dashed border-border p-12 text-center">
          <p className="text-muted-foreground">
            Failed to load channel videos. Make sure you have a YouTube channel linked.
          </p>
        </div>
      ) : allVideos.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-12 text-center">
          <p className="text-muted-foreground">No videos found on your channel.</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {allVideos.map((video) => (
              <Card key={video.youtube_video_id} className="overflow-hidden">
                <div className="relative aspect-video bg-muted">
                  {video.thumbnail_url ? (
                    <img
                      src={video.thumbnail_url}
                      alt={video.title}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center">
                      <PlayCircle className="h-10 w-10 text-muted-foreground" />
                    </div>
                  )}
                  <span className="absolute bottom-2 right-2 rounded bg-black/75 px-1.5 py-0.5 text-xs text-white">
                    {formatDuration(video.duration_seconds)}
                  </span>
                </div>
                <CardContent className="p-4">
                  <h3 className="line-clamp-2 text-sm font-medium leading-snug">
                    {video.title}
                  </h3>
                  <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground">
                    {video.view_count != null && (
                      <span>{formatNumber(video.view_count)} views</span>
                    )}
                    <span>{timeAgo(video.published_at)}</span>
                  </div>
                  <Button
                    className="mt-3 w-full"
                    size="sm"
                    disabled={video.already_analyzed || analyzeMutation.isPending}
                    onClick={() => handleAnalyze(video.youtube_video_id)}
                  >
                    {video.already_analyzed ? "Already Analyzed" : "Analyze"}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>

          {hasNextPage && (
            <div className="flex justify-center">
              <Button
                variant="outline"
                onClick={() => fetchNextPage()}
                disabled={isFetchingNextPage}
              >
                {isFetchingNextPage ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Loading...
                  </>
                ) : (
                  "Load More"
                )}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
