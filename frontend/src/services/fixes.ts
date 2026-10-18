import type { FixSuggestion } from "../types/fix";
import { ApiError, request } from "./api";

/** Return the saved suggestion, or null if none has been generated yet. */
export async function fetchFix(
  findingId: string,
  signal?: AbortSignal,
): Promise<FixSuggestion | null> {
  try {
    return await request<FixSuggestion>(`/api/findings/${encodeURIComponent(findingId)}/fix`, {
      signal,
    });
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

/** Ask the backend to propose a patch (or return the cached one). Nothing is applied. */
export function suggestFix(findingId: string, refresh: boolean): Promise<FixSuggestion> {
  const query = refresh ? "?refresh=true" : "";
  return request<FixSuggestion>(
    `/api/findings/${encodeURIComponent(findingId)}/suggest-fix${query}`,
    { method: "POST" },
  );
}
