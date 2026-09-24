import { redirect } from "next/navigation";
import { api } from "./api";
import { setToken, clearToken } from "./cookies";
import type {
  LoginPayload,
  RegisterPayload,
  TokenResponse,
  User,
} from "./types";

export async function login(payload: LoginPayload): Promise<User> {
  const { data } = await api.post<TokenResponse>("/api/v1/auth/login", payload);
  setToken(data.access_token);
  return data.user;
}

export async function register(payload: RegisterPayload): Promise<User> {
  const { data } = await api.post<TokenResponse>(
    "/api/v1/auth/register",
    payload,
  );
  setToken(data.access_token);
  return data.user;
}

export function logout(): void {
  clearToken();
  redirect("/login");
}

export async function fetchCurrentUser(): Promise<User> {
  const { data } = await api.get<User>("/api/v1/auth/me");
  return data;
}
