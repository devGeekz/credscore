"use client";

import { useState } from "react";
import useSWR from "swr";
import { UploadStatementForm } from "@/components/merchants/UploadStatementForm";
import { useMerchants } from "@/hooks/useMerchants";
import { formatDate } from "@/lib/format";
import {
  listStatements,
  requeueStatement,
  type Statement,
} from "@/lib/statements";

const STATUS_STYLES: Record<Statement["parse_status"], string> = {
  pending: "bg-amber-100 text-amber-800",
  parsed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

export default function MerchantsPage() {
  const { merchants, isLoading } = useMerchants();
  const { data: statements, mutate: refreshStatements } = useSWR(
    "/api/v1/statements",
    () => listStatements(),
    // poll only while something is still being parsed
    {
      refreshInterval: (data) =>
        data?.some((statement) => statement.parse_status === "pending") ? 3000 : 0,
    },
  );
  const [requeueing, setRequeueing] = useState<string | null>(null);

  async function handleRequeue(statementId: string) {
    setRequeueing(statementId);
    try {
      await requeueStatement(statementId);
      await refreshStatements();
    } finally {
      setRequeueing(null);
    }
  }

  // statements arrive newest-first, so the first hit per merchant is its latest.
  const latestByMerchant = new Map<string, Statement>();
  statements?.forEach((statement) => {
    if (!latestByMerchant.has(statement.merchant_id)) {
      latestByMerchant.set(statement.merchant_id, statement);
    }
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Applicants</h1>
        <p className="mt-1 text-sm text-gray-500">
          Merchant applicants and their statement status.
        </p>
      </div>

      <section className="rounded-lg border border-gray-200 bg-white">
        {isLoading ? (
          <p className="px-5 py-6 text-sm text-gray-500">Loading…</p>
        ) : merchants.length === 0 ? (
          <p className="px-5 py-6 text-sm text-gray-500">
            No applicants yet — add one while uploading a statement below.
          </p>
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-gray-500">
                <th className="px-5 py-2">Applicant</th>
                <th className="py-2">Phone</th>
                <th className="py-2">Consent</th>
                <th className="py-2">Latest statement</th>
                <th className="py-2 pr-5">Added</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {merchants.map((merchant) => {
                const latest = latestByMerchant.get(merchant.id);
                return (
                  <tr key={merchant.id} className="hover:bg-gray-50">
                    <td className="px-5 py-2.5">
                      <div className="font-medium text-gray-900">{merchant.full_name}</div>
                      {merchant.business_name && (
                        <div className="text-xs text-gray-500">{merchant.business_name}</div>
                      )}
                    </td>
                    <td className="py-2.5 font-mono text-xs">{merchant.phone}</td>
                    <td className="py-2.5">
                      {merchant.consent_verified ? (
                        <span className="text-xs text-green-700">
                          verified {formatDate(merchant.consent_timestamp)}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400">not verified</span>
                      )}
                    </td>
                    <td className="py-2.5">
                      {latest ? (
                        <span className="flex items-center gap-2">
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[latest.parse_status]}`}
                          >
                            {latest.parse_status}
                          </span>
                          {latest.parse_status === "failed" && (
                            <button
                              onClick={() => handleRequeue(latest.id)}
                              disabled={requeueing === latest.id}
                              className="text-xs text-blue-600 hover:underline disabled:opacity-50"
                            >
                              {requeueing === latest.id ? "Retrying…" : "Retry"}
                            </button>
                          )}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400">none</span>
                      )}
                    </td>
                    <td className="py-2.5 pr-5 text-gray-500">
                      {formatDate(merchant.created_at)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          </div>
        )}
      </section>

      <div className="max-w-2xl">
        <UploadStatementForm />
      </div>
    </div>
  );
}
