interface SnippetViewProps {
  snippet: string;
  lineStart: number;
  lineEnd: number;
}

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

export default function SnippetView({ snippet, lineStart, lineEnd }: SnippetViewProps) {
  return (
    <div
      role="region"
      aria-label="Source snippet"
      tabIndex={0}
      className="overflow-x-auto rounded-md bg-gray-900 py-2 font-mono text-xs text-gray-100"
    >
      {parseRows(snippet).map((row, index) => {
        const flagged = row.number !== null && row.number >= lineStart && row.number <= lineEnd;
        return (
          <div key={index} className={`flex px-3 ${flagged ? "bg-amber-400/20" : ""}`}>
            <span className="w-10 shrink-0 select-none pr-3 text-right text-gray-500">
              {row.number ?? ""}
            </span>
            <span className="whitespace-pre">{row.code}</span>
          </div>
        );
      })}
    </div>
  );
}
