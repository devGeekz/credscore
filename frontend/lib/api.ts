import axios from "axios";

/**
 * Single axios instance every hook/page imports from. Attaches the JWT
 * from localStorage automatically, and redirects to /login on a 401 so
 * an expired/invalid token doesn't leave the UI silently broken.
 */
export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("credscore_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (typeof window !== "undefined" && error.response?.status === 401) {
      localStorage.removeItem("credscore_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);