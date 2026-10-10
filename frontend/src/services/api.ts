import type { HealthResponse } from "../types/health";

// Empty in development (Vite proxies /api). Set VITE_API_BASE_URL when deploying.
const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "";

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/health`, { signal });
  if (!response.ok) {
    throw new Error(`Backend responded with status ${response.status}`);
  }
  return (await response.json()) as HealthResponse;
}
