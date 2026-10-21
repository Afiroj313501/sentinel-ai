import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  deleteScan,
  fetchFindings,
  fetchHealth,
  fetchReportBlob,
  fetchScans,
  scanGithub,
  uploadScan,
} from "./api";
import { explainFinding, fetchExplanation } from "./explanations";
import { fetchFix } from "./fixes";
import type { FindingsQuery } from "../types/scan";

const fetchMock = vi.fn();

function mockFetch(response: Response): void {
  fetchMock.mockResolvedValue(response);
  vi.stubGlobal("fetch", fetchMock);
}

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status });
}

function lastCall(): { url: string; init: RequestInit } {
  const [url, init] = fetchMock.mock.calls[fetchMock.mock.calls.length - 1];
  return { url: String(url), init: (init ?? {}) as RequestInit };
}

afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

describe("API client errors", () => {
  it("returns parsed JSON on success", async () => {
    mockFetch(json(200, { status: "ok" }));
    await expect(fetchHealth()).resolves.toEqual({ status: "ok" });
    expect(lastCall().url).toBe("/api/health");
  });

  it("uses the server's detail message for errors", async () => {
    mockFetch(json(404, { detail: "Scan not found." }));
    const error = await fetchHealth().catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).message).toBe("Scan not found.");
    expect((error as ApiError).status).toBe(404);
  });

  it.each([
    ["a non-JSON body", new Response("<html>oops</html>", { status: 500 }), "Request failed with status 500."],
    ["JSON without detail", json(500, { other: 1 }), "Request failed with status 500."],
    ["a validation list as detail", json(422, { detail: [{ msg: "bad" }] }), "Request failed with status 422."],
  ])("falls back to a generic message for %s", async (_label, response, expected) => {
    mockFetch(response);
    await expect(fetchHealth()).rejects.toThrow(expected);
  });

  it("reports an unreachable backend as an ApiError with status 0", async () => {
    fetchMock.mockRejectedValue(new TypeError("network error"));
    vi.stubGlobal("fetch", fetchMock);
    await expect(fetchHealth()).rejects.toMatchObject({
      status: 0,
      message: "Cannot reach the Sentinel backend. Is it running?",
    });
  });

  it("lets aborted requests through untouched so callers can ignore them", async () => {
    const aborted = new DOMException("aborted", "AbortError");
    fetchMock.mockRejectedValue(aborted);
    vi.stubGlobal("fetch", fetchMock);
    await expect(fetchHealth()).rejects.toBe(aborted);
  });

  it("returns undefined for 204 responses and uses the DELETE method", async () => {
    mockFetch(new Response(null, { status: 204 }));
    await expect(deleteScan("abc")).resolves.toBeUndefined();
    expect(lastCall().init.method).toBe("DELETE");
    expect(lastCall().url).toBe("/api/scans/abc");
  });
});

describe("API client requests", () => {
  it("builds the scan list query", async () => {
    mockFetch(json(200, { total: 0, limit: 10, offset: 20, items: [] }));
    await fetchScans(10, 20);
    expect(lastCall().url).toBe("/api/scans?limit=10&offset=20");
  });

  it("builds the findings query and encodes the scan id", async () => {
    mockFetch(json(200, { total: 0, limit: 20, offset: 40, items: [] }));
    const query: FindingsQuery = {
      severity: ["high", "low"],
      category: ["security"],
      scanner: ["bandit"],
      q: "eval",
      filePath: "src/",
      limit: 20,
      offset: 40,
    };
    await fetchFindings("a/b", query);
    const { url } = lastCall();
    expect(url.startsWith("/api/scans/a%2Fb/findings?")).toBe(true);
    const params = new URL(url, "http://localhost").searchParams;
    expect(params.getAll("severity")).toEqual(["high", "low"]);
    expect(params.getAll("category")).toEqual(["security"]);
    expect(params.getAll("scanner")).toEqual(["bandit"]);
    expect(params.get("q")).toBe("eval");
    expect(params.get("file_path")).toBe("src/");
    expect(params.get("limit")).toBe("20");
    expect(params.get("offset")).toBe("40");
  });

  it("leaves empty filters out of the query", async () => {
    mockFetch(json(200, { total: 0, limit: 20, offset: 0, items: [] }));
    await fetchFindings("abc", {
      severity: [], category: [], scanner: [], q: "", filePath: "", limit: 20, offset: 0,
    });
    const params = new URL(lastCall().url, "http://localhost").searchParams;
    expect([...params.keys()].sort()).toEqual(["limit", "offset"]);
  });

  it("uploads the file as multipart form data without a manual content type", async () => {
    mockFetch(json(200, {}));
    await uploadScan(new File(["PK"], "repo.zip"));
    const { url, init } = lastCall();
    expect(url).toBe("/api/scans/upload");
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
    expect((init.body as FormData).get("file")).toBeInstanceOf(File);
    expect(init.headers).toBeUndefined();
  });

  it("posts the GitHub URL as JSON", async () => {
    mockFetch(json(200, {}));
    await scanGithub("https://github.com/octocat/Hello-World");
    const { url, init } = lastCall();
    expect(url).toBe("/api/scans/github");
    expect(init.method).toBe("POST");
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(String(init.body))).toEqual({ url: "https://github.com/octocat/Hello-World" });
  });

  it("requests reports with the chosen format and AI option", async () => {
    mockFetch(new Response("# report"));
    const blob = await fetchReportBlob("abc", "markdown", true);
    expect(lastCall().url).toBe("/api/scans/abc/report?format=markdown&include_ai=true");
    expect(await blob.text()).toBe("# report");
  });

  it("surfaces a report error message from the server", async () => {
    mockFetch(json(404, { detail: "Scan not found." }));
    await expect(fetchReportBlob("abc", "json", false)).rejects.toThrow("Scan not found.");
  });
});

describe("saved AI results", () => {
  it.each([
    ["explanation", () => fetchExplanation("f-1")],
    ["fix suggestion", () => fetchFix("f-1")],
  ])("treat a 404 on the saved %s as 'none yet'", async (_label, load) => {
    mockFetch(json(404, { detail: "No result has been generated yet." }));
    await expect(load()).resolves.toBeNull();
  });

  it.each([
    ["explanation", () => fetchExplanation("f-1")],
    ["fix suggestion", () => fetchFix("f-1")],
  ])("still raise other errors for the saved %s", async (_label, load) => {
    mockFetch(json(500, { detail: "Server error." }));
    await expect(load()).rejects.toThrow("Server error.");
  });

  it("returns the saved explanation when it exists", async () => {
    mockFetch(json(200, { finding_id: "f-1", summary: "s" }));
    await expect(fetchExplanation("f-1")).resolves.toMatchObject({ finding_id: "f-1" });
    expect(lastCall().url).toBe("/api/findings/f-1/explanation");
  });

  it("adds refresh only when regenerating", async () => {
    fetchMock.mockImplementation(() => Promise.resolve(json(200, {})));
    vi.stubGlobal("fetch", fetchMock);
    await explainFinding("f-1", false);
    expect(lastCall().url).toBe("/api/findings/f-1/explain");
    expect(lastCall().init.method).toBe("POST");
    await explainFinding("f-1", true);
    expect(lastCall().url).toBe("/api/findings/f-1/explain?refresh=true");
  });
});
