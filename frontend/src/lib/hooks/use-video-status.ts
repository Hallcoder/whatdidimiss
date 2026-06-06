"use client";

import { useQuery } from "@tanstack/react-query";
import { getVideoStatus } from "@/lib/api/videos";

export function useVideoStatus(videoId: string, enabled = true) {
  return useQuery({
    queryKey: ["video-status", videoId],
    queryFn: () => getVideoStatus(videoId),
    enabled: !!videoId && enabled,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed") return false;
      return 3000;
    },
  });
}
