import apiClient from "./client";
import type { AuthURLResponse, TokenResponse, UserResponse } from "./types";

export async function getGoogleLoginUrl(): Promise<AuthURLResponse> {
  const { data } = await apiClient.get<AuthURLResponse>("/api/v1/auth/google/login");
  return data;
}

export async function refreshToken(): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/api/v1/auth/refresh");
  return data;
}

export async function logout(): Promise<void> {
  await apiClient.post("/api/v1/auth/logout");
}

export async function getMe(): Promise<UserResponse> {
  const { data } = await apiClient.get<UserResponse>("/api/v1/auth/me");
  return data;
}
