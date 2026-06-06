import apiClient from "./client";
import type {
  AnalysisResponse,
  EngagementResponse,
  EngagementSegment,
  TranscriptSegment,
} from "./types";

export async function getAnalysis(videoId: string): Promise<AnalysisResponse> {
  const { data } = await apiClient.get<AnalysisResponse>(`/api/v1/videos/${videoId}/analysis`);
  return data;
}

export async function getTranscript(videoId: string): Promise<{ segments: TranscriptSegment[] }> {
  const { data } = await apiClient.get<{ segments: TranscriptSegment[] }>(
    `/api/v1/videos/${videoId}/analysis/transcript`
  );
  return data;
}

export async function getEngagement(videoId: string): Promise<EngagementResponse> {
  const { data } = await apiClient.get<EngagementResponse>(
    `/api/v1/videos/${videoId}/engagement`
  );
  return data;
}

export async function getEngagementSegments(videoId: string): Promise<EngagementSegment[]> {
  const { data } = await apiClient.get<EngagementSegment[]>(
    `/api/v1/videos/${videoId}/engagement/segments`
  );
  return data;
}
