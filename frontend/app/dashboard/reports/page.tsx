"use client";

import Link from "next/link";
import { useState } from "react";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { useReports } from "@/hooks/useReports";
import { formatDate, formatCedis, formatPercent } from "@/lib/format";
import { reportsExportUrl, type RiskTag } from "@/lib/reports";

const FILTERS: { value: string; label: string }[] = [
  { value: "", label: "All risk tags" },
  { value: "strong", label: "Strong" },
  { value: "moderate", label: "Moderate" },
  { value: "high_risk", label: "High risk" },
];

export default function ReportsPage() {
  const [riskTag, setRiskTag] = useState("");
  const { reports, isLoading } = useReports({ risk_tag: riskTag });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Score reports</h1>
          <p className="mt-1 text-sm text-gray-500">
            Every statement scored for your organisation.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={riskTag}
            onChange={(event) => setRiskTag(event.target.value)}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {FILTERS.map((filter) => (
              <option key={filter.value} value={filter.value}>
                {filter.label}
              </option>
            ))}
          </select>
          <a
            href={reportsExportUrl({ risk_tag: riskTag })}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Export CSV
          </a>
        </div>
      </div>

      <section className="rounded-lg border border-gray-200 bg-white">
        {isLoading ? (
          <p className="px-5 py-6 text-sm text-gray-500">Loading…</p>
        ) : reports.length === 0 ? (
          <p className="px-5 py-6 text-sm text-gray-500">No reports match this filter.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-gray-500">
                <th className="px-5 py-2">Applicant</th>
                <th className="py-2">Risk</th>
                <th className="py-2">Net revenue</th>
                <th className="py-2">Consistency</th>
                <th className="py-2">Suggested limit</th>
                <th className="py-2 pr-5">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {reports.map((report) => (
                <tr key={report.id} className="hover:bg-gray-50">
                  <td className="px-5 py-2.5">
                    <Link
                      href={`/dashboard/reports/${report.id}`}
                      className="font-medium text-gray-900 hover:underline"
                    >
                      {report.merchant.full_name}
                    </Link>
                  </td>
                  <td className="py-2.5">
                    <RiskBadge tag={report.risk_tag as RiskTag} />
                  </td>
                  <td className="py-2.5">{formatCedis(report.net_verified_revenue)}</td>
                  <td className="py-2.5 text-gray-500">
                    {formatPercent(report.cash_flow_consistency)}
                  </td>
                  <td className="py-2.5">{formatCedis(report.suggested_credit_limit)}</td>
                  <td className="py-2.5 pr-5 text-gray-500">
                    {formatDate(report.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
