"use client";

import { useQuery } from "@tanstack/react-query";
import { getInsights } from "@/lib/api/insights";

export function useInsights(videoId: string, type?: string) {
  return useQuery({
    queryKey: ["insights", videoId, type],
    queryFn: () => getInsights(videoId, type),
    enabled: !!videoId,
  });
}
