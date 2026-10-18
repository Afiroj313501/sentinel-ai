const HUNK = /^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/;

type Row =
  | { kind: "file" | "hunk"; text: string }
  | { kind: "context" | "add" | "del"; oldNo: number | null; newNo: number | null; text: string };

function parseDiff(diff: string): Row[] {
  const rows: Row[] = [];
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
    // File headers only appear before the first hunk; afterwards "--- " is just a deleted line.
    if (!inHunk) {
      rows.push({ kind: "file", text: line });
      continue;
    }
    if (line.startsWith("\\")) continue; // "\ No newline at end of file"

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

/** Shows a unified diff. Content is rendered as text, never as HTML. */
export default function DiffView({ diff }: { diff: string }) {
  return (
    <div className="diff" role="region" aria-label="Proposed patch" tabIndex={0}>
      {parseDiff(diff).map((row, index) => {
        if (row.kind === "file") {
          return (
            <div key={index} className="diff-file">
              {row.text}
            </div>
          );
        }
        if (row.kind === "hunk") {
          return (
            <div key={index} className="diff-hunk">
              {row.text}
            </div>
          );
        }
        if (row.kind !== "context" && row.kind !== "add" && row.kind !== "del") {
          return null;
        }
        const sign = row.kind === "add" ? "+" : row.kind === "del" ? "-" : " ";
        return (
          <div key={index} className={`diff-row diff-${row.kind}`}>
            <span className="diff-num">{row.oldNo ?? ""}</span>
            <span className="diff-num">{row.newNo ?? ""}</span>
            <span className="diff-sign">{sign}</span>
            <span className="diff-code">{row.text}</span>
          </div>
        );
      })}
    </div>
  );
}
