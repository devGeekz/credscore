"use client";

import { useState } from "react";
import useSWR from "swr";
import type { AxiosError } from "axios";
import {
  fetchSettings,
  fetchWebhookDeliveries,
  updateSettings,
} from "@/lib/settings";
import type { ApiErrorResponse } from "@/lib/types";

export default function SettingsPage() {
  const { data: settings, mutate } = useSWR("/api/v1/settings", fetchSettings);
  const { data: deliveries } = useSWR(
    "/api/v1/settings/webhooks",
    fetchWebhookDeliveries,
  );
  // null until the user types — derived value follows swr data otherwise
  const [urlOverride, setUrlOverride] = useState<string | null>(null);
  const url = urlOverride ?? settings?.webhook_url ?? "";
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function handleSave(rotate = false) {
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await updateSettings({ webhook_url: url, rotate_webhook_secret: rotate });
      await mutate();
      setUrlOverride(null);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (err) {
      const axiosErr = err as AxiosError<ApiErrorResponse>;
      setError(axiosErr.response?.data?.error?.message || "Could not save settings.");
    } finally {
      setBusy(false);
    }
  }

  const usage = settings?.usage;

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Settings</h1>
        <p className="mt-1 text-sm text-gray-500">
          Organisation profile, plan usage, and score webhooks.
        </p>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
      )}
      {saved && (
        <div className="rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">
          Settings saved.
        </div>
      )}

      <section className="rounded-lg border border-gray-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-gray-900">Organisation</h2>
        <dl className="mt-3 grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-gray-500">Name</dt>
            <dd className="text-gray-900">{settings?.name ?? "…"}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Type</dt>
            <dd className="text-gray-900">{settings?.org_type ?? "…"}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Contact</dt>
            <dd className="text-gray-900">{settings?.contact_email ?? "…"}</dd>
          </div>
        </dl>
      </section>

      <section className="rounded-lg border border-gray-200 bg-white p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-900">Plan &amp; usage</h2>
          {usage && (
            <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium uppercase text-gray-700">
              {usage.plan} · {usage.status}
            </span>
          )}
        </div>
        {usage && (
          <div className="mt-3">
            <div className="flex items-baseline justify-between text-sm">
              <span className="text-gray-600">
                Statements this month ({usage.month})
              </span>
              <span className="font-medium text-gray-900">
                {usage.statements_used}
                {usage.statements_included !== null
                  ? ` of ${usage.statements_included}`
                  : ""}
              </span>
            </div>
            {usage.statements_included !== null && (
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-gray-100">
                <div
                  className={`h-full rounded-full ${
                    usage.overage > 0 ? "bg-amber-500" : "bg-gray-900"
                  }`}
                  style={{
                    width: `${Math.min(
                      100,
                      Math.round(
                        (usage.statements_used / usage.statements_included) * 100,
                      ),
                    )}%`,
                  }}
                />
              </div>
            )}
            <p className="mt-2 text-xs text-gray-500">
              {usage.overage > 0 ? `${usage.overage} over the included volume. ` : ""}
              {usage.price_monthly !== null
                ? `₦${usage.price_monthly.toLocaleString()}/month`
                : "Custom pricing"}
              {usage.seats !== null ? ` · ${usage.seats} seat${usage.seats > 1 ? "s" : ""}` : ""}
            </p>
          </div>
        )}
      </section>

      <section className="rounded-lg border border-gray-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-gray-900">Score webhook</h2>
        <p className="mt-1 text-sm text-gray-600">
          We POST a signed <code className="text-xs">score.completed</code> event here
          after every parse.
        </p>

        <label className="mt-4 block text-xs font-medium text-gray-700" htmlFor="webhook-url">
          Endpoint URL
        </label>
        <div className="mt-1 flex gap-2">
          <input
            id="webhook-url"
            type="url"
            value={url}
            onChange={(e) => setUrlOverride(e.target.value)}
            placeholder="https://your-lender.example/hooks/credscore"
            className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-gray-900 focus:outline-none"
          />
          <button
            onClick={() => handleSave(false)}
            disabled={busy}
            className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
          >
            Save
          </button>
        </div>

        {settings?.webhook_secret && (
          <div className="mt-4 flex items-center gap-2">
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-gray-700">Signing secret</p>
              <code className="block overflow-x-auto whitespace-nowrap rounded bg-gray-50 px-2 py-1 text-xs text-gray-800">
                {settings.webhook_secret}
              </code>
            </div>
            <button
              onClick={() => handleSave(true)}
              disabled={busy}
              className="shrink-0 rounded-md border border-gray-300 px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              Rotate
            </button>
          </div>
        )}
        <p className="mt-3 text-xs text-gray-500">
          Verify with{" "}
          <code className="text-[11px]">sha256=HMAC_SHA256(secret, raw_body)</code> in the{" "}
          <code className="text-[11px]">X-CredScore-Signature</code> header.
        </p>
      </section>

      <section className="rounded-lg border border-gray-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-gray-900">Recent deliveries</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-xs uppercase text-gray-500">
                <th className="py-2 pr-4">Event</th>
                <th className="py-2 pr-4">Status</th>
                <th className="py-2 pr-4">Attempts</th>
                <th className="py-2 pr-4">Response</th>
                <th className="py-2">When</th>
              </tr>
            </thead>
            <tbody>
              {!deliveries?.length && (
                <tr>
                  <td colSpan={5} className="py-4 text-center text-gray-500">
                    No deliveries yet.
                  </td>
                </tr>
              )}
              {deliveries?.map((delivery) => (
                <tr key={delivery.id} className="border-b border-gray-100 text-gray-700">
                  <td className="py-2 pr-4">{delivery.event_type}</td>
                  <td className="py-2 pr-4">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        delivery.delivered
                          ? "bg-green-100 text-green-800"
                          : "bg-amber-100 text-amber-800"
                      }`}
                    >
                      {delivery.delivered ? "Delivered" : "Pending"}
                    </span>
                  </td>
                  <td className="py-2 pr-4">{delivery.attempts}</td>
                  <td className="py-2 pr-4">{delivery.response_status ?? "—"}</td>
                  <td className="py-2 text-xs text-gray-500">
                    {new Date(delivery.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
