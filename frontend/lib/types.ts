export interface User {
  id: string;
  tenant_id: string;
  email: string;
  name: string;
  role: "admin" | "underwriter" | "viewer";
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface RegisterPayload {
  tenant_name: string;
  org_type: string;
  contact_email: string;
  admin_name: string;
  admin_email: string;
  password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface ApiErrorResponse {
  detail?: string;
  error?: { code: string; message: string };
}