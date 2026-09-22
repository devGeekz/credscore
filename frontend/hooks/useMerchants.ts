import useSWR from "swr";
import { listMerchants, type Merchant } from "@/lib/merchants";

export function useMerchants() {
  const { data, error, isLoading, mutate } = useSWR<Merchant[]>("/api/v1/merchants", listMerchants);
  return { merchants: data ?? [], isLoading, error, mutate };
}