"use client";

import { useState } from "react";
import useSWR from "swr";
import { createApiKey, fetchApiKey, revokeApiKey } from "@/lib/apikeys";
import type { AxiosError } from "axios";
import type { ApiErrorResponse } from "@/lib/types";

export default function ApiKeysPage() {
  const { data: keyState, mutate } = useSWR("/api/v1/auth/api-keys", fetchApiKey);
  const [freshKey, setFreshKey] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function handleCreate() {
    setBusy(true);
    setError(null);
    try {
      const created = await createApiKey();
      setFreshKey(created.api_key);
      await mutate();
    } catch (err) {
      const axiosErr = err as AxiosError<ApiErrorResponse>;
      setError(axiosErr.response?.data?.error?.message || "Could not create a key.");
    } finally {
      setBusy(false);
    }
  }

  async function handleRevoke() {
    setBusy(true);
    setError(null);
    try {
      await revokeApiKey();
      setFreshKey(null);
      await mutate();
    } catch (err) {
      const axiosErr = err as AxiosError<ApiErrorResponse>;
      setError(axiosErr.response?.data?.error?.message || "Could not revoke the key.");
    } finally {
      setBusy(false);
    }
  }

  async function copyKey() {
    if (!freshKey) return;
    await navigator.clipboard.writeText(freshKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">API keys</h1>
        <p className="mt-1 text-sm text-gray-500">
          Server-to-server key for pushing scores into your loan system.
        </p>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
      )}

      {freshKey && (
        <div className="rounded-md border border-amber-300 bg-amber-50 p-4">
          <p className="text-sm font-medium text-amber-900">
            Copy this key now — it is not shown again.
          </p>
          <div className="mt-2 flex items-center gap-2">
            <code className="block flex-1 overflow-x-auto rounded bg-white px-3 py-2 text-xs text-gray-800">
              {freshKey}
            </code>
            <button
              onClick={copyKey}
              className="rounded-md bg-gray-900 px-3 py-2 text-xs font-medium text-white hover:bg-gray-800"
            >
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        </div>
      )}

      <section className="rounded-lg border border-gray-200 bg-white p-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-gray-900">Current key</h2>
            <p className="mt-1 text-sm text-gray-600">
              {keyState?.active
                ? `${keyState.masked} — active`
                : keyState
                  ? "No key yet"
                  : "Loading…"}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleCreate}
              disabled={busy}
              className="rounded-md bg-gray-900 px-3 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
            >
              {keyState?.active ? "Regenerate" : "Generate key"}
            </button>
            {keyState?.active && (
              <button
                onClick={handleRevoke}
                disabled={busy}
                className="rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Revoke
              </button>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
