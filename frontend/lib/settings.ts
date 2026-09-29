import { api } from "./api";

export interface PlanUsage {
  plan: string;
  status: string;
  month: string;
  statements_used: number;
  statements_included: number | null;
  overage: number;
  price_monthly: number | null;
  seats: number | null;
}

export interface Settings {
  name: string;
  org_type: string;
  contact_email: string;
  subscription_plan: string;
  subscription_status: string;
  webhook_url: string | null;
  webhook_secret: string | null;
  usage: PlanUsage;
}

export interface WebhookDelivery {
  id: string;
  event_type: string;
  delivered: boolean;
  attempts: string;
  response_status: string | null;
  created_at: string;
}

export interface SettingsUpdate {
  webhook_url: string;
  rotate_webhook_secret?: boolean;
}

export async function fetchSettings(): Promise<Settings> {
  const { data } = await api.get<Settings>("/api/v1/settings");
  return data;
}

export async function updateSettings(payload: SettingsUpdate): Promise<Settings> {
  const { data } = await api.put<Settings>("/api/v1/settings", payload);
  return data;
}

export async function fetchWebhookDeliveries(): Promise<WebhookDelivery[]> {
  const { data } = await api.get<WebhookDelivery[]>("/api/v1/settings/webhooks");
  return data;
}
