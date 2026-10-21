import { describe, expect, it } from "vitest";
import { formatBytes, formatRelative } from "./format";

describe("formatBytes", () => {
  it.each([
    [0, "0 B"],
    [1023, "1023 B"],
    [1024, "1.0 KB"],
    [1536, "1.5 KB"],
    [1024 * 1024, "1.0 MB"],
    [25 * 1024 * 1024, "25.0 MB"],
  ])("formats %i bytes as %s", (bytes, expected) => {
    expect(formatBytes(bytes)).toBe(expected);
  });
});

describe("formatRelative", () => {
  const now = Date.parse("2026-10-20T12:00:00Z");
  const ago = (seconds: number) => new Date(now - seconds * 1000).toISOString();

  it.each([
    [0, "just now"],
    [44, "just now"],
    [45, "1m ago"],
    [5 * 60, "5m ago"],
    [3 * 3600, "3h ago"],
    [2 * 86400, "2d ago"],
  ])("formats %i seconds ago as %s", (seconds, expected) => {
    expect(formatRelative(ago(seconds), now)).toBe(expected);
  });

  it("treats times in the future as just now", () => {
    expect(formatRelative(new Date(now + 60_000).toISOString(), now)).toBe("just now");
  });

  it("falls back to a calendar date after two weeks", () => {
    const iso = ago(30 * 86400);
    expect(formatRelative(iso, now)).toBe(new Date(iso).toLocaleDateString());
  });
});
