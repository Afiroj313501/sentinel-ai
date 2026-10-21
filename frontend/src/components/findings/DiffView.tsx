import { parseDiff } from "../../services/diff";

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
