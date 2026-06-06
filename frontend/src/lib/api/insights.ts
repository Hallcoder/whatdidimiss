import apiClient from "./client";
import type { InsightsResponse } from "./types";

export async function getInsights(videoId: string, type?: string): Promise<InsightsResponse> {
  const { data } = await apiClient.get<InsightsResponse>(
    `/api/v1/videos/${videoId}/insights`,
    { params: type ? { type } : undefined }
  );
  return data;
}
