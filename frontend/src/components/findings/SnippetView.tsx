import { parseSnippet } from "../../services/snippet";

interface SnippetViewProps {
  snippet: string;
  lineStart: number;
  lineEnd: number;
}

/** Shows scanner-captured source. Content is rendered as text, never as HTML. */
export default function SnippetView({ snippet, lineStart, lineEnd }: SnippetViewProps) {
  return (
    <div className="snippet" role="region" aria-label="Source snippet" tabIndex={0}>
      {parseSnippet(snippet).map((row, index) => {
        const flagged = row.number !== null && row.number >= lineStart && row.number <= lineEnd;
        return (
          <div key={index} className={`snippet-row${flagged ? " flagged" : ""}`}>
            <span className="snippet-num">{row.number ?? ""}</span>
            <span className="snippet-code">{row.code}</span>
          </div>
        );
      })}
    </div>
  );
}
