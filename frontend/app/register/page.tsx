"use client";

import { useState } from "react";
import Link from "next/link";
import { register } from "@/lib/auth";
import type { AxiosError } from "axios";
import type { ApiErrorResponse } from "@/lib/types";

const ORG_TYPES = [
  { value: "mfi", label: "Microfinance Institution" },
  { value: "bank", label: "Bank" },
  { value: "fintech_lender", label: "Fintech Lender" },
];

export default function RegisterPage() {
  const [form, setForm] = useState({
    tenant_name: "",
    org_type: "mfi",
    contact_email: "",
    admin_name: "",
    admin_email: "",
    password: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function update(field: keyof typeof form, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await register(form);
      window.location.href = "/dashboard";
    } catch (err) {
      const axiosErr = err as AxiosError<ApiErrorResponse>;
      setError(
        axiosErr.response?.data?.detail ||
          axiosErr.response?.data?.error?.message ||
          "Something went wrong. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-semibold text-gray-900">Register your organization</h1>
          <p className="mt-1 text-sm text-gray-500">Creates your org and your admin account</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
          )}

          <div>
            <label htmlFor="tenant_name" className="block text-sm font-medium text-gray-700">
              Organization name
            </label>
            <input
              id="tenant_name"
              required
              value={form.tenant_name}
              onChange={(e) => update("tenant_name", e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="Accra Microfinance"
            />
          </div>

          <div>
            <label htmlFor="org_type" className="block text-sm font-medium text-gray-700">
              Organization type
            </label>
            <select
              id="org_type"
              value={form.org_type}
              onChange={(e) => update("org_type", e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {ORG_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="contact_email" className="block text-sm font-medium text-gray-700">
              Organization contact email
            </label>
            <input
              id="contact_email"
              type="email"
              required
              value={form.contact_email}
              onChange={(e) => update("contact_email", e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="ops@accramfi.com"
            />
          </div>

          <hr className="border-gray-200" />

          <div>
            <label htmlFor="admin_name" className="block text-sm font-medium text-gray-700">
              Your name
            </label>
            <input
              id="admin_name"
              required
              value={form.admin_name}
              onChange={(e) => update("admin_name", e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label htmlFor="admin_email" className="block text-sm font-medium text-gray-700">
              Your email
            </label>
            <input
              id="admin_email"
              type="email"
              required
              value={form.admin_email}
              onChange={(e) => update("admin_email", e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              value={form.password}
              onChange={(e) => update("password", e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <p className="mt-1 text-xs text-gray-400">At least 8 characters</p>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-gray-900 px-3 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
          >
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-gray-900 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}