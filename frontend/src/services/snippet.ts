const LINE_PATTERN = /^\s*(\d+) \| ?(.*)$/;

export interface SnippetRow {
  number: number | null;
  code: string;
}

export function parseSnippet(snippet: string): SnippetRow[] {
  return snippet.split("\n").map((raw) => {
    const match = LINE_PATTERN.exec(raw);
    return match ? { number: Number(match[1]), code: match[2] } : { number: null, code: raw };
  });
}
