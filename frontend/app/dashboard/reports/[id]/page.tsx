"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { fetchReport, type ReportDetail } from "@/lib/reports";
import { formatDate, formatCedis, formatPercent } from "@/lib/format";
import useSWR from "swr";

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-gray-500">
        {label}
      </div>
      <div className="mt-1 text-lg font-semibold text-gray-900">{value}</div>
    </div>
  );
}

export default function ReportDetailPage() {
  const params = useParams<{ id: string }>();
  const { data: report, isLoading, error } = useSWR<ReportDetail>(
    params.id ? `/api/v1/reports/${params.id}` : null,
    () => fetchReport(params.id),
  );

  if (isLoading) {
    return <p className="text-sm text-gray-500">Loading report…</p>;
  }
  if (error || !report) {
    return <p className="text-sm text-red-600">Could not load this report.</p>;
  }

  const chartData = (report.raw_payload?.daily_revenue ?? []).map(
    ([day, amount]) => ({ day: day.slice(5), amount }),
  );
  const excluded = report.raw_payload?.excluded_amounts;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="text-sm text-gray-500">
            <Link href="/dashboard/reports" className="hover:text-gray-900">
              Reports
            </Link>{" "}
            / {report.merchant.full_name}
          </div>
          <div className="mt-1 flex items-center gap-3">
            <h1 className="text-xl font-semibold text-gray-900">
              {report.merchant.full_name}
            </h1>
            <RiskBadge tag={report.risk_tag} />
          </div>
          <p className="mt-1 text-sm text-gray-500">
            {report.source_channel === "whatsapp" ? "WhatsApp" : "Web upload"} ·{" "}
            {formatDate(report.period_start)} – {formatDate(report.period_end)}
          </p>
        </div>
        <Link
          href="/dashboard/reports"
          className="rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Back to reports
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        <Metric
          label="Net verified revenue"
          value={formatCedis(report.net_verified_revenue, true)}
        />
        <Metric
          label="Suggested credit limit"
          value={formatCedis(report.suggested_credit_limit, true)}
        />
        <Metric
          label="Average daily balance"
          value={formatCedis(report.average_daily_balance)}
        />
        <Metric
          label="Cash-flow consistency"
          value={formatPercent(report.cash_flow_consistency)}
        />
        <Metric label="Expense ratio" value={formatPercent(report.expense_ratio)} />
        <Metric
          label="Counterparty concentration"
          value={formatPercent(report.counterparty_concentration)}
        />
      </div>

      <section className="rounded-lg border border-gray-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-gray-900">Daily business revenue</h2>
        {chartData.length === 0 ? (
          <p className="mt-3 text-sm text-gray-500">No daily breakdown available.</p>
        ) : (
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
                <defs>
                  <linearGradient id="revenue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#111827" stopOpacity={0.25} />
                    <stop offset="100%" stopColor="#111827" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(value) => formatCedis(Number(value))} />
                <Area
                  type="monotone"
                  dataKey="amount"
                  stroke="#111827"
                  fill="url(#revenue)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      {excluded && (
        <section className="rounded-lg border border-gray-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-gray-900">
            Excluded from verified revenue
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Personal transfers {formatCedis(excluded.personal, true)} · internal sweeps{" "}
            {formatCedis(excluded.internal, true)} · cash-outs{" "}
            {formatCedis(excluded.cash_out, true)} ·{" "}
            {report.raw_payload?.active_days ?? 0} active days
          </p>
        </section>
      )}
    </div>
  );
}
