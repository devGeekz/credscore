import { api } from "./api";

export interface DashboardStats {
  merchants: number;
  statements_this_month: number;
  statements_pending: number;
  reports: number;
  risk_mix: Record<string, number>;
  average_credit_limit: number | null;
}

export async function fetchStats(): Promise<DashboardStats> {
  const { data } = await api.get<DashboardStats>("/api/v1/dashboard/stats");
  return data;
}
