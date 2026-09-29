import useSWR from "swr";
import { fetchStats, type DashboardStats } from "@/lib/dashboard";

export function useDashboardStats() {
  const { data, error, isLoading, mutate } = useSWR<DashboardStats>(
    "/api/v1/dashboard/stats",
    fetchStats,
  );
  return { stats: data, isLoading, error, mutate };
}
