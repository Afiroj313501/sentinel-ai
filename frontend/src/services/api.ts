import type { HealthResponse } from "../types/health";
import type { ScanResult } from "../types/finding";
import type { FindingsPage, FindingsQuery, ScanDetail, ScanListPage } from "../types/scan";

// Empty in development (Vite proxies /api). Set VITE_API_BASE_URL when deploying.
const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (typeof body === "object" && body !== null && "detail" in body && typeof body.detail === "string") {
      return body.detail;
    }
  } catch {
    return `Request failed with status ${response.status}.`;
  }
  return `Request failed with status ${response.status}.`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init);
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError("Cannot reach the Sentinel backend. Is it running?", 0);
  }
  if (!response.ok) throw new ApiError(await errorMessage(response), response.status);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health", { signal });
}

export function uploadScan(file: File, signal?: AbortSignal): Promise<ScanResult> {
  const form = new FormData();
  form.append("file", file);
  return request<ScanResult>("/api/scans/upload", { method: "POST", body: form, signal });
}

export function fetchScans(limit: number, offset: number, signal?: AbortSignal): Promise<ScanListPage> {
  return request<ScanListPage>(`/api/scans?limit=${limit}&offset=${offset}`, { signal });
}

export function fetchScan(scanId: string, signal?: AbortSignal): Promise<ScanDetail> {
  return request<ScanDetail>(`/api/scans/${encodeURIComponent(scanId)}`, { signal });
}

export function deleteScan(scanId: string): Promise<void> {
  return request<void>(`/api/scans/${encodeURIComponent(scanId)}`, { method: "DELETE" });
}

export function fetchFindings(
  scanId: string,
  query: FindingsQuery,
  signal?: AbortSignal,
): Promise<FindingsPage> {
  const params = new URLSearchParams();
  query.severity.forEach((value) => params.append("severity", value));
  query.category.forEach((value) => params.append("category", value));
  query.scanner.forEach((value) => params.append("scanner", value));
  if (query.q) params.set("q", query.q);
  if (query.filePath) params.set("file_path", query.filePath);
  params.set("limit", String(query.limit));
  params.set("offset", String(query.offset));
  return request<FindingsPage>(`/api/scans/${encodeURIComponent(scanId)}/findings?${params}`, { signal });
}
