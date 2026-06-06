"use client";

import { useQuery } from "@tanstack/react-query";
import { getDashboard } from "@/lib/api/dashboard";

export function useDashboard(videoId: string) {
  return useQuery({
    queryKey: ["dashboard", videoId],
    queryFn: () => getDashboard(videoId),
    enabled: !!videoId,
  });
}
