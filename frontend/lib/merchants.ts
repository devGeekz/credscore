import { api } from "./api";

export interface Merchant {
  id: string;
  tenant_id: string;
  full_name: string;
  phone: string;
  business_name: string | null;
  telco: string | null;
  consent_verified: boolean;
  created_at: string;
}

export interface CreateMerchantPayload {
  full_name: string;
  phone: string;
  business_name?: string;
  telco?: string;
}

export async function listMerchants(): Promise<Merchant[]> {
  const { data } = await api.get<Merchant[]>("/api/v1/merchants");
  return data;
}

export async function createMerchant(payload: CreateMerchantPayload): Promise<Merchant> {
  const { data } = await api.post<Merchant>("/api/v1/merchants", payload);
  return data;
}