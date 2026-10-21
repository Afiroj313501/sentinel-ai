const HUNK = /^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/;

export type DiffRow =
  | { kind: "file" | "hunk"; text: string }
  | { kind: "context" | "add" | "del"; oldNo: number | null; newNo: number | null; text: string };

export function parseDiff(diff: string): DiffRow[] {
  const rows: DiffRow[] = [];
  const lines = diff.split("\n");
  if (lines[lines.length - 1] === "") lines.pop();

  let oldNo = 0;
  let newNo = 0;
  let inHunk = false;

  for (const line of lines) {
    const hunk = HUNK.exec(line);
    if (hunk) {
      oldNo = Number(hunk[1]);
      newNo = Number(hunk[2]);
      inHunk = true;
      rows.push({ kind: "hunk", text: line });
      continue;
    }
    if (!inHunk) {
      rows.push({ kind: "file", text: line });
      continue;
    }
    if (line.startsWith("\\")) continue;

    const sign = line[0];
    const text = line.slice(1);
    if (sign === "+") {
      rows.push({ kind: "add", oldNo: null, newNo: newNo++, text });
    } else if (sign === "-") {
      rows.push({ kind: "del", oldNo: oldNo++, newNo: null, text });
    } else {
      rows.push({ kind: "context", oldNo: oldNo++, newNo: newNo++, text });
    }
  }
  return rows;
}
