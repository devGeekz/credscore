const TOKEN_COOKIE = "credscore_token";
const REFRESH_COOKIE = "credscore_refresh";
const HOUR_SECONDS = 60 * 60;
const SEVEN_DAYS_SECONDS = 60 * 60 * 24 * 7;

function write(name: string, value: string, maxAgeSeconds: number): void {
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAgeSeconds}; SameSite=Lax`;
}

function read(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export function setToken(token: string): void {
  if (typeof document === "undefined") return;
  write(TOKEN_COOKIE, token, HOUR_SECONDS); // access tokens live ~1 hour
}

export function getToken(): string | null {
  if (typeof document === "undefined") return null;
  return read(TOKEN_COOKIE);
}

export function setRefreshToken(token: string): void {
  if (typeof document === "undefined") return;
  write(REFRESH_COOKIE, token, SEVEN_DAYS_SECONDS);
}

export function getRefreshToken(): string | null {
  if (typeof document === "undefined") return null;
  return read(REFRESH_COOKIE);
}

export function clearToken(): void {
  if (typeof document === "undefined") return;
  document.cookie = `${TOKEN_COOKIE}=; path=/; max-age=0`;
  document.cookie = `${REFRESH_COOKIE}=; path=/; max-age=0`;
}
