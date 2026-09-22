"use client";

import { useState } from "react";
import { useMerchants } from "@/hooks/useMerchants";
import { createMerchant } from "@/lib/merchants";
import { uploadStatement, type Statement } from "@/lib/statements";
import type { AxiosError } from "axios";
import type { ApiErrorResponse } from "@/lib/types";

export function UploadStatementForm() {
  const { merchants, isLoading: merchantsLoading, mutate: refreshMerchants } = useMerchants();

  const [merchantId, setMerchantId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [lastResult, setLastResult] = useState<Statement | null>(null);

  const [showQuickAdd, setShowQuickAdd] = useState(false);
  const [quickAddForm, setQuickAddForm] = useState({ full_name: "", phone: "" });
  const [quickAddLoading, setQuickAddLoading] = useState(false);

  async function handleQuickAdd(e: React.FormEvent) {
    e.preventDefault();
    setQuickAddLoading(true);
    setError(null);
    try {
      const merchant = await createMerchant(quickAddForm);
      await refreshMerchants();
      setMerchantId(merchant.id);
      setShowQuickAdd(false);
      setQuickAddForm({ full_name: "", phone: "" });
    } catch (err) {
      const axiosErr = err as AxiosError<ApiErrorResponse>;
      setError(axiosErr.response?.data?.error?.message || "Couldn't create merchant.");
    } finally {
      setQuickAddLoading(false);
    }
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!merchantId || !file) return;

    setError(null);
    setLastResult(null);
    setUploading(true);
    try {
      const statement = await uploadStatement(merchantId, file);
      setLastResult(statement);
      setFile(null);
    } catch (err) {
      const axiosErr = err as AxiosError<ApiErrorResponse>;
      setError(
        axiosErr.response?.data?.error?.message ||
          axiosErr.response?.data?.detail ||
          "Upload failed."
      );
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <h2 className="text-sm font-semibold text-gray-900">Upload a MoMo statement</h2>

      {error && (
        <div className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
      )}

      {lastResult && (
        <div className="mt-3 rounded-md bg-green-50 px-3 py-2 text-sm text-green-800">
          Uploaded — statement <span className="font-mono">{lastResult.id.slice(0, 8)}</span> is{" "}
          <span className="font-medium">{lastResult.parse_status}</span>.
        </div>
      )}

      <form onSubmit={handleUpload} className="mt-4 space-y-4">
        <div>
          <label htmlFor="merchant" className="block text-sm font-medium text-gray-700">
            Applicant
          </label>
          <div className="mt-1 flex gap-2">
            <select
              id="merchant"
              value={merchantId}
              onChange={(e) => setMerchantId(e.target.value)}
              disabled={merchantsLoading}
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">
                {merchantsLoading ? "Loading..." : "Select an applicant"}
              </option>
              {merchants.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.full_name} — {m.phone}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => setShowQuickAdd((v) => !v)}
              className="whitespace-nowrap rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              + New
            </button>
          </div>
        </div>

        {showQuickAdd && (
          <div className="rounded-md border border-gray-200 bg-gray-50 p-3 space-y-2">
            <input
              placeholder="Full name"
              value={quickAddForm.full_name}
              onChange={(e) => setQuickAddForm((f) => ({ ...f, full_name: e.target.value }))}
              className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
            />
            <input
              placeholder="Phone (e.g. +233201234567)"
              value={quickAddForm.phone}
              onChange={(e) => setQuickAddForm((f) => ({ ...f, phone: e.target.value }))}
              className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
            />
            <button
              type="button"
              onClick={handleQuickAdd}
              disabled={quickAddLoading || !quickAddForm.full_name || !quickAddForm.phone}
              className="rounded-md bg-gray-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
            >
              {quickAddLoading ? "Adding..." : "Add applicant"}
            </button>
          </div>
        )}

        <div>
          <label htmlFor="file" className="block text-sm font-medium text-gray-700">
            Statement file (PDF or CSV)
          </label>
          <input
            id="file"
            type="file"
            accept=".pdf,.csv,application/pdf,text/csv"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="mt-1 block w-full text-sm text-gray-600 file:mr-3 file:rounded-md file:border-0 file:bg-gray-100 file:px-3 file:py-2 file:text-sm file:font-medium hover:file:bg-gray-200"
          />
        </div>

        <button
          type="submit"
          disabled={uploading || !merchantId || !file}
          className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
        >
          {uploading ? "Uploading..." : "Upload statement"}
        </button>
      </form>
    </div>
  );
}