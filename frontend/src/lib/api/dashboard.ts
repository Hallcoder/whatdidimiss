import apiClient from "./client";
import type { DashboardResponse } from "./types";

export async function getDashboard(videoId: string): Promise<DashboardResponse> {
  const { data } = await apiClient.get<DashboardResponse>(`/api/v1/dashboard/${videoId}`);
  return data;
}
