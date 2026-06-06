"use client";

import { useQuery } from "@tanstack/react-query";
import { getAnalysis, getTranscript } from "@/lib/api/analysis";

export function useAnalysis(videoId: string) {
  return useQuery({
    queryKey: ["analysis", videoId],
    queryFn: () => getAnalysis(videoId),
    enabled: !!videoId,
  });
}

export function useTranscript(videoId: string) {
  return useQuery({
    queryKey: ["transcript", videoId],
    queryFn: () => getTranscript(videoId),
    enabled: !!videoId,
  });
}
