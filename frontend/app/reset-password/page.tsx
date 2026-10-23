"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { clearToken } from "@/lib/cookies";
import type { AxiosError } from "axios";
import type { ApiErrorResponse } from "@/lib/types";

function ResetPasswordForm() {
  const router = useRouter();
  const search = useSearchParams();
  const token = search.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await api.post("/api/v1/auth/reset-password", { token, new_password: password });
      // any old session is dead after this — start clean
      clearToken();
      setDone(true);
      setTimeout(() => router.push("/login"), 2500);
    } catch (err) {
      const axiosErr = err as AxiosError<ApiErrorResponse>;
      setError(
        axiosErr.response?.data?.error?.message ||
          axiosErr.response?.data?.detail ||
          "This reset link is invalid or has expired.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full max-w-sm space-y-6">
      <div className="text-center">
        <h1 className="text-2xl font-semibold text-gray-900">Choose a new password</h1>
      </div>

      {done ? (
        <div className="rounded-md bg-green-50 px-3 py-3 text-sm text-green-700">
          Password updated. All sessions were signed out — taking you to sign in…
        </div>
      ) : !token ? (
        <div className="rounded-md bg-red-50 px-3 py-3 text-sm text-red-700">
          No reset token in the link.{" "}
          <Link href="/forgot-password" className="underline">
            Request a new one
          </Link>
          .
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
          )}
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">
              New password
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <p className="mt-1 text-xs text-gray-400">At least 8 characters</p>
          </div>
          <div>
            <label htmlFor="confirm" className="block text-sm font-medium text-gray-700">
              Confirm new password
            </label>
            <input
              id="confirm"
              type="password"
              required
              minLength={8}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-gray-900 px-3 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
          >
            {loading ? "Saving..." : "Update password"}
          </button>
        </form>
      )}

      <p className="text-center text-sm text-gray-500">
        <Link href="/login" className="font-medium text-gray-900 hover:underline">
          Back to sign in
        </Link>
      </p>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <Suspense fallback={null}>
        <ResetPasswordForm />
      </Suspense>
    </div>
  );
}
