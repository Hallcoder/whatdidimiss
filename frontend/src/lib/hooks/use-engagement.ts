"use client";

import { useQuery } from "@tanstack/react-query";
import { getEngagement, getEngagementSegments } from "@/lib/api/analysis";

export function useEngagement(videoId: string) {
  return useQuery({
    queryKey: ["engagement", videoId],
    queryFn: () => getEngagement(videoId),
    enabled: !!videoId,
  });
}

export function useEngagementSegments(videoId: string) {
  return useQuery({
    queryKey: ["engagement-segments", videoId],
    queryFn: () => getEngagementSegments(videoId),
    enabled: !!videoId,
  });
}
