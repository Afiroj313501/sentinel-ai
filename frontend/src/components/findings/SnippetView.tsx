interface SnippetViewProps {
  snippet: string;
  lineStart: number;
  lineEnd: number;
}

// The backend formats each snippet line as "<number> | <code>".
const LINE_PATTERN = /^\s*(\d+) \| ?(.*)$/;

interface Row {
  number: number | null;
  code: string;
}

function parseRows(snippet: string): Row[] {
  return snippet.split("\n").map((raw) => {
    const match = LINE_PATTERN.exec(raw);
    return match ? { number: Number(match[1]), code: match[2] } : { number: null, code: raw };
  });
}

/** Shows scanner-captured source. Content is rendered as text, never as HTML. */
export default function SnippetView({ snippet, lineStart, lineEnd }: SnippetViewProps) {
  return (
    <div className="snippet" role="region" aria-label="Source snippet" tabIndex={0}>
      {parseRows(snippet).map((row, index) => {
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
