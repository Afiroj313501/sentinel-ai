import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import SeverityBadge from "../common/SeverityBadge";
import SnippetView from "./SnippetView";
import type { Finding } from "../../types/finding";

export default function FindingCard({ finding }: { finding: Finding }) {
  const [open, setOpen] = useState(false);
  const lines = finding.line_end > finding.line_start
    ? `${finding.line_start}-${finding.line_end}`
    : `${finding.line_start}`;
  const Chevron = open ? ChevronDown : ChevronRight;

  return (
    <li className="rounded-lg border border-gray-200 bg-white">
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="flex w-full items-start gap-3 p-4 text-left">
        <Chevron className="mt-0.5 h-4 w-4 shrink-0 text-gray-400" aria-hidden="true" />
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-2"><SeverityBadge severity={finding.severity} /><span className="font-medium">{finding.title}</span></span>
          <span className="mt-1 block truncate font-mono text-xs text-gray-500">{finding.file_path}:{lines}</span>
          <span className="mt-1 block text-xs text-gray-500">{finding.scanner} · {finding.rule_id}</span>
        </span>
      </button>
      {open && (
        <div className="space-y-3 border-t border-gray-100 p-4 text-sm">
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500">Scanner evidence</h3>
            <p className="mt-1 text-gray-800">{finding.evidence}</p>
            <p className="mt-1 text-xs text-gray-500">Confidence: {finding.confidence}{finding.cwe ? ` · ${finding.cwe}` : ""}</p>
          </div>
          {finding.snippet ? <SnippetView snippet={finding.snippet} lineStart={finding.line_start} lineEnd={finding.line_end} /> : <p className="text-xs text-gray-500">No source snippet is available for this finding.</p>}
        </div>
      )}
    </li>
  );
}
