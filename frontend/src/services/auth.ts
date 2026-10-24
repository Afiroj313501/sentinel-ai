import { request } from "./api";
import { clearToken, getToken, setToken } from "./token";
import type { AuthPayload, TokenResponse, User } from "../types/auth";

export { clearToken, getToken, setToken };

export async function loginUser(payload: AuthPayload): Promise<TokenResponse> {
  const result = await request<TokenResponse>("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  setToken(result.access_token);
  return result;
}

export async function registerUser(payload: AuthPayload): Promise<TokenResponse> {
  const result = await request<TokenResponse>("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  setToken(result.access_token);
  return result;
}

export function fetchCurrentUser(signal?: AbortSignal): Promise<User> {
  return request<User>("/api/auth/me", { signal });
}
