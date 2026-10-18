import type { Explanation } from "../types/explanation";
import { ApiError, request } from "./api";

export async function fetchExplanation(
  findingId: string,
  signal?: AbortSignal,
): Promise<Explanation | null> {
  try {
    return await request<Explanation>(
      `/api/findings/${encodeURIComponent(findingId)}/explanation`,
      { signal },
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export function explainFinding(findingId: string, refresh: boolean): Promise<Explanation> {
  const query = refresh ? "?refresh=true" : "";
  return request<Explanation>(`/api/findings/${encodeURIComponent(findingId)}/explain${query}`, {
    method: "POST",
  });
}
