import { describe, expect, it } from "vitest";
import { parseDiff } from "./diff";

const DIFF =
  "--- a/src/app.py\n+++ b/src/app.py\n@@ -10,3 +10,3 @@\n a\n-eval(x)\n+int(x)\n c\n";

describe("parseDiff", () => {
  it("numbers old and new lines from the hunk header", () => {
    const rows = parseDiff(DIFF);
    expect(rows.map((row) => row.kind)).toEqual(["file", "file", "hunk", "context", "del", "add", "context"]);
    expect(rows[3]).toEqual({ kind: "context", oldNo: 10, newNo: 10, text: "a" });
    expect(rows[4]).toEqual({ kind: "del", oldNo: 11, newNo: null, text: "eval(x)" });
    expect(rows[5]).toEqual({ kind: "add", oldNo: null, newNo: 11, text: "int(x)" });
    expect(rows[6]).toEqual({ kind: "context", oldNo: 12, newNo: 12, text: "c" });
  });

  it("treats a deleted line that starts with dashes as a deletion", () => {
    const rows = parseDiff("--- a/f\n+++ b/f\n@@ -1,2 +1,1 @@\n--- not a header\n keep\n");
    expect(rows[3]).toEqual({ kind: "del", oldNo: 1, newNo: null, text: "-- not a header" });
  });

  it("treats an added line that starts with pluses as an addition", () => {
    const rows = parseDiff("--- a/f\n+++ b/f\n@@ -1,1 +1,2 @@\n keep\n+++ added\n");
    expect(rows[4]).toEqual({ kind: "add", oldNo: null, newNo: 2, text: "++ added" });
  });

  it("restarts numbering at each hunk", () => {
    const rows = parseDiff("--- a/f\n+++ b/f\n@@ -1,1 +1,1 @@\n a\n@@ -20,1 +20,1 @@\n b\n");
    expect(rows[3]).toMatchObject({ kind: "context", oldNo: 1, newNo: 1 });
    expect(rows[5]).toMatchObject({ kind: "context", oldNo: 20, newNo: 20, text: "b" });
  });

  it("skips no-newline markers and accepts stripped empty context lines", () => {
    const rows = parseDiff("--- a/f\n+++ b/f\n@@ -1,3 +1,3 @@\n a\n\n-b\n\\ No newline at end of file\n+c\n");
    expect(rows.map((row) => row.kind)).toEqual(["file", "file", "hunk", "context", "context", "del", "add"]);
    expect(rows[4]).toMatchObject({ kind: "context", oldNo: 2, newNo: 2, text: "" });
  });

  it("returns nothing for an empty diff and never interprets markup", () => {
    expect(parseDiff("")).toEqual([]);
    const rows = parseDiff("--- a/f\n+++ b/f\n@@ -1,1 +1,1 @@\n-<img src=x onerror=alert(1)>\n+ok\n");
    expect(rows[3]).toMatchObject({ kind: "del", text: "<img src=x onerror=alert(1)>" });
  });
});
