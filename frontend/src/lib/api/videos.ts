import apiClient from "./client";
import type {
  ChannelVideosResponse,
  PaginatedResponse,
  SelfAssessmentData,
  VideoAnalyzeResponse,
  VideoDetailResponse,
  VideoStatusResponse,
  VideoSummary,
  VideoUploadResponse,
} from "./types";

export async function analyzeVideo(youtubeUrl: string): Promise<VideoAnalyzeResponse> {
  const { data } = await apiClient.post<VideoAnalyzeResponse>("/api/v1/videos/analyze", {
    youtube_url: youtubeUrl,
  });
  return data;
}

export async function uploadVideo(
  file: File,
  title?: string,
  onProgress?: (pct: number) => void,
): Promise<VideoUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (title) formData.append("title", title);

  const { data } = await apiClient.post<VideoUploadResponse>("/api/v1/videos/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (e) => {
      if (e.total && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    },
  });
  return data;
}

export async function browseChannelVideos(
  pageToken?: string,
): Promise<ChannelVideosResponse> {
  const { data } = await apiClient.get<ChannelVideosResponse>("/api/v1/videos/channel-videos", {
    params: pageToken ? { page_token: pageToken } : undefined,
  });
  return data;
}

export async function listVideos(params?: {
  page?: number;
  per_page?: number;
  status?: string;
}): Promise<PaginatedResponse<VideoSummary>> {
  const { data } = await apiClient.get<PaginatedResponse<VideoSummary>>("/api/v1/videos", {
    params,
  });
  return data;
}

export async function getVideo(videoId: string): Promise<VideoDetailResponse> {
  const { data } = await apiClient.get<VideoDetailResponse>(`/api/v1/videos/${videoId}`);
  return data;
}

export async function getVideoStatus(videoId: string): Promise<VideoStatusResponse> {
  const { data } = await apiClient.get<VideoStatusResponse>(`/api/v1/videos/${videoId}/status`);
  return data;
}

export async function deleteVideo(videoId: string): Promise<void> {
  await apiClient.delete(`/api/v1/videos/${videoId}`);
}

export async function reanalyzeVideo(videoId: string): Promise<VideoAnalyzeResponse> {
  const { data } = await apiClient.post<VideoAnalyzeResponse>(
    `/api/v1/videos/${videoId}/reanalyze`,
  );
  return data;
}

export async function submitSelfAssessment(
  videoId: string,
  assessment: Omit<SelfAssessmentData, "submitted_at">,
): Promise<SelfAssessmentData> {
  const { data } = await apiClient.post<SelfAssessmentData>(
    `/api/v1/videos/${videoId}/self-assessment`,
    assessment,
  );
  return data;
}

export async function getSelfAssessment(videoId: string): Promise<SelfAssessmentData> {
  const { data } = await apiClient.get<SelfAssessmentData>(
    `/api/v1/videos/${videoId}/self-assessment`,
  );
  return data;
}
