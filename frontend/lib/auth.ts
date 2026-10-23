import { redirect } from "next/navigation";
import { api } from "./api";
import {
  clearToken,
  setRefreshToken,
  setToken,
  getRefreshToken,
} from "./cookies";
import type {
  LoginPayload,
  RegisterPayload,
  TokenResponse,
  User,
} from "./types";

async function storeTokens(data: TokenResponse): Promise<User> {
  setToken(data.access_token);
  if (data.refresh_token) setRefreshToken(data.refresh_token);
  return data.user;
}

export async function login(payload: LoginPayload): Promise<User> {
  const { data } = await api.post<TokenResponse>("/api/v1/auth/login", payload);
  return storeTokens(data);
}

export async function register(payload: RegisterPayload): Promise<User> {
  const { data } = await api.post<TokenResponse>(
    "/api/v1/auth/register",
    payload,
  );
  return storeTokens(data);
}

export async function logout(): Promise<void> {
  const refresh = getRefreshToken();
  try {
    if (refresh) {
      // revokes the session server-side; cookie clearing is best-effort
      await api.post("/api/v1/auth/logout", { refresh_token: refresh });
    }
  } catch {
    // already signed out or network gone — cookies get cleared regardless
  }
  clearToken();
  redirect("/login");
}

export async function fetchCurrentUser(): Promise<User> {
  const { data } = await api.get<User>("/api/v1/auth/me");
  return data;
}

export async function fetchTeam(): Promise<User[]> {
  const { data } = await api.get<User[]>("/api/v1/auth/users");
  return data;
}

export async function createTeamMember(payload: {
  name: string;
  email: string;
  password: string;
  role: string;
}): Promise<User> {
  const { data } = await api.post<User>("/api/v1/auth/users", payload);
  return data;
}
