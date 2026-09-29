import { api } from "./api";

export interface ApiKeyState {
  masked: string | null;
  active: boolean;
}

export interface ApiKeyCreated extends ApiKeyState {
  api_key: string;
}

export async function fetchApiKey(): Promise<ApiKeyState> {
  const { data } = await api.get<ApiKeyState>("/api/v1/auth/api-keys");
  return data;
}

export async function createApiKey(): Promise<ApiKeyCreated> {
  const { data } = await api.post<ApiKeyCreated>("/api/v1/auth/api-keys");
  return data;
}

export async function revokeApiKey(): Promise<void> {
  await api.delete("/api/v1/auth/api-keys");
}
