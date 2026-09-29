import useSWR from "swr";
import { listReports, type ReportFilters, type ReportSummary } from "@/lib/reports";

export function useReports(filters: ReportFilters = {}) {
  const key = ["/api/v1/reports", filters] as const;
  const { data, error, isLoading, mutate } = useSWR<ReportSummary[]>(
    key,
    () => listReports(filters),
  );
  return { reports: data ?? [], isLoading, error, mutate };
}
