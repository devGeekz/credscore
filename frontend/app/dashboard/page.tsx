"use client";

import Link from "next/link";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { UploadStatementForm } from "@/components/merchants/UploadStatementForm";
import { useDashboardStats } from "@/hooks/useDashboardStats";
import { useReports } from "@/hooks/useReports";
import { formatDate, formatCedis, riskLabel } from "@/lib/format";

export default function DashboardPage() {
  const { stats } = useDashboardStats();
  const { reports } = useReports();
  const recent = reports.slice(0, 5);

  const cards = [
    { label: "Applicants", value: stats ? String(stats.merchants) : "—" },
    {
      label: "Statements this month",
      value: stats ? String(stats.statements_this_month) : "—",
    },
    { label: "Score reports", value: stats ? String(stats.reports) : "—" },
    { label: "Avg. credit limit", value: formatCedis(stats?.average_credit_limit) },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Overview</h1>
        {stats && (
          <p className="mt-1 text-sm text-gray-500">
            {Object.entries(stats.risk_mix)
              .map(([tag, count]) => `${count} ${riskLabel(tag)}`)
              .join(" · ")}
            {stats.statements_pending > 0 &&
              ` · ${stats.statements_pending} statement(s) pending`}
          </p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {cards.map((card) => (
          <div key={card.label} className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-gray-500">
              {card.label}
            </div>
            <div className="mt-1 text-2xl font-semibold text-gray-900">{card.value}</div>
          </div>
        ))}
      </div>

      <section className="rounded-lg border border-gray-200 bg-white">
        <div className="flex items-center justify-between border-b border-gray-200 px-5 py-3">
          <h2 className="text-sm font-semibold text-gray-900">Recent score reports</h2>
          <Link
            href="/dashboard/reports"
            className="text-sm font-medium text-gray-600 hover:text-gray-900"
          >
            View all
          </Link>
        </div>
        {recent.length === 0 ? (
          <p className="px-5 py-6 text-sm text-gray-500">
            No reports yet — upload a statement below.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-gray-500">
                <th className="px-5 py-2">Applicant</th>
                <th className="py-2">Risk</th>
                <th className="py-2">Net revenue</th>
                <th className="py-2">Suggested limit</th>
                <th className="py-2 pr-5">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {recent.map((report) => (
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
                    <RiskBadge tag={report.risk_tag} />
                  </td>
                  <td className="py-2.5">{formatCedis(report.net_verified_revenue)}</td>
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

      <div className="max-w-2xl">
        <UploadStatementForm />
      </div>
    </div>
  );
}
