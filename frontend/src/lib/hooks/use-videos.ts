"use client";

import { useState } from "react";
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import type { SelfAssessmentData } from "@/lib/api/types";
import {
  analyzeVideo,
  browseChannelVideos,
  deleteVideo,
  getSelfAssessment,
  listVideos,
  reanalyzeVideo,
  submitSelfAssessment,
  uploadVideo,
} from "@/lib/api/videos";

export function useVideos(params?: { page?: number; status?: string }) {
  return useQuery({
    queryKey: ["videos", params],
    queryFn: () => listVideos(params),
  });
}

export function useAnalyzeVideo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (url: string) => analyzeVideo(url),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["videos"] });
    },
  });
}

export function useUploadVideo() {
  const queryClient = useQueryClient();
  const [uploadProgress, setUploadProgress] = useState(0);

  const mutation = useMutation({
    mutationFn: ({ file, title }: { file: File; title?: string }) =>
      uploadVideo(file, title, setUploadProgress),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["videos"] });
      setUploadProgress(0);
    },
    onError: () => {
      setUploadProgress(0);
    },
  });

  return { ...mutation, uploadProgress };
}

export function useChannelVideos() {
  return useInfiniteQuery({
    queryKey: ["channel-videos"],
    queryFn: ({ pageParam }) => browseChannelVideos(pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_page_token ?? undefined,
  });
}

export function useReanalyzeVideo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (videoId: string) => reanalyzeVideo(videoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["videos"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useSelfAssessment(videoId: string) {
  return useQuery({
    queryKey: ["self-assessment", videoId],
    queryFn: () => getSelfAssessment(videoId),
    retry: false,
  });
}

export function useSubmitSelfAssessment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      videoId,
      data,
    }: {
      videoId: string;
      data: Omit<SelfAssessmentData, "submitted_at">;
    }) => submitSelfAssessment(videoId, data),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["self-assessment", variables.videoId],
      });
    },
  });
}

export function useDeleteVideo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (videoId: string) => deleteVideo(videoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["videos"] });
    },
  });
}
