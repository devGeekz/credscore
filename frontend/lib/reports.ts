import { api } from "./api";

export type RiskTag = "strong" | "moderate" | "high_risk";

export interface ReportMerchant {
  id: string;
  full_name: string;
}

export interface ReportSummary {
  id: string;
  statement_id: string;
  merchant: ReportMerchant;
  risk_tag: RiskTag | null;
  net_verified_revenue: number | null;
  cash_flow_consistency: number | null;
  suggested_credit_limit: number | null;
  created_at: string;
}

export interface ReportDetail extends ReportSummary {
  cash_flow_consistency: number | null;
  average_daily_balance: number | null;
  expense_ratio: number | null;
  counterparty_concentration: number | null;
  source_channel: string | null;
  period_start: string | null;
  period_end: string | null;
  raw_payload: {
    daily_revenue?: [string, number][];
    active_days?: number;
    monthly_average_revenue?: number;
    excluded_amounts?: Record<string, number>;
    top_counterparties?: { name: string; amount: number }[];
    period?: { start: string; end: string; days: number };
  } | null;
}

export interface ReportFilters {
  risk_tag?: string;
  merchant_id?: string;
}

export async function listReports(filters: ReportFilters = {}): Promise<ReportSummary[]> {
  const { data } = await api.get<ReportSummary[]>("/api/v1/reports", {
    params: Object.fromEntries(Object.entries(filters).filter(([, v]) => v)),
  });
  return data;
}

export async function fetchReport(id: string): Promise<ReportDetail> {
  const { data } = await api.get<ReportDetail>(`/api/v1/reports/${id}`);
  return data;
}

export function reportsExportUrl(filters: ReportFilters = {}): string {
  const params = new URLSearchParams(
    Object.entries(filters).filter(([, v]) => v) as [string, string][],
  );
  const query = params.toString();
  return `${process.env.NEXT_PUBLIC_API_URL}/api/v1/reports/export${query ? `?${query}` : ""}`;
}
