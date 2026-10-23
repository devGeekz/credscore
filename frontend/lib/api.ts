import axios from "axios";
import {
  clearToken,
  getToken,
  getRefreshToken,
  setRefreshToken,
  setToken,
} from "./cookies";
import { redirect } from "next/navigation";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshInFlight: Promise<string> | null = null;

function refreshAccessToken(): Promise<string> {
  refreshInFlight ??= api
    .post("/api/v1/auth/refresh", { refresh_token: getRefreshToken() })
    .then(({ data }) => {
      setToken(data.access_token);
      if (data.refresh_token) setRefreshToken(data.refresh_token);
      return data.access_token as string;
    })
    .finally(() => {
      refreshInFlight = null;
    });
  return refreshInFlight;
}

function isAuthCall(url?: string): boolean {
  return !!url && url.includes("/auth/");
}

// login/register answer 401 for bad credentials — that is a form error the
// page must render, not a session expiry worth redirecting for
function isCredentialCall(url?: string): boolean {
  return !!url && (url.includes("/auth/login") || url.includes("/auth/register"));
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config ?? {};
    const status = error.response?.status;

    // expired access token -> rotate the refresh once, then retry silently
    if (
      typeof window !== "undefined" &&
      status === 401 &&
      getRefreshToken() &&
      !original._retried &&
      !isAuthCall(original.url)
    ) {
      try {
        const token = await refreshAccessToken();
        original._retried = true;
        original.headers = { ...original.headers, Authorization: `Bearer ${token}` };
        return api(original);
      } catch {
        // fall through to the hard 401 handling below
      }
    }

    if (typeof window !== "undefined" && status === 401 && !isCredentialCall(original.url)) {
      clearToken();
      redirect("/login");
    }
    return Promise.reject(error);
  },
);
