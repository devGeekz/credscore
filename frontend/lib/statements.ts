import { api } from "./api";

export interface Statement {
  id: string;
  merchant_id: string;
  source_channel: string;
  parse_status: "pending" | "parsed" | "failed";
  created_at: string;
}

export async function uploadStatement(merchantId: string, file: File): Promise<Statement> {
  const formData = new FormData();
  formData.append("merchant_id", merchantId);
  formData.append("file", file);

  const { data } = await api.post<Statement>("/api/v1/statements/upload", formData);
  return data;
}

export async function listStatements(merchantId?: string): Promise<Statement[]> {
  const { data } = await api.get<Statement[]>("/api/v1/statements", {
    params: merchantId ? { merchant_id: merchantId } : {},
  });
  return data;
}

export async function requeueStatement(statementId: string): Promise<Statement> {
  const { data } = await api.post<Statement>(
    `/api/v1/statements/${statementId}/requeue`,
  );
  return data;
}