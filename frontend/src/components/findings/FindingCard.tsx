import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import SeverityBadge from "../common/SeverityBadge";
import ExplanationPanel from "./ExplanationPanel";
import SnippetView from "./SnippetView";
import type { Finding } from "../../types/finding";

interface FindingCardProps {
  finding: Finding;
}

export default function FindingCard({ finding }: FindingCardProps) {
  const [open, setOpen] = useState(false);
  const lines =
    finding.line_end > finding.line_start
      ? `${finding.line_start}-${finding.line_end}`
      : `${finding.line_start}`;
  const Chevron = open ? ChevronDown : ChevronRight;

  return (
    <li className="finding">
      <button
        type="button"
        className="finding-toggle"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <Chevron className="chev" aria-hidden="true" />
        <span style={{ minWidth: 0, flex: 1 }}>
          <span className="finding-title-row">
            <SeverityBadge severity={finding.severity} />
            <span>{finding.title}</span>
          </span>
          <span className="finding-meta mono ellipsis">
            {finding.file_path}:{lines}
          </span>
          <span className="finding-meta">
            {finding.scanner} Â· {finding.rule_id}
          </span>
        </span>
      </button>

      {open && (
        <div className="finding-body">
          <div>
            <p className="label">Scanner evidence</p>
            <p className="body-text">{finding.evidence}</p>
            <p className="fine-print">
              Confidence: {finding.confidence}
              {finding.cwe ? ` Â· ${finding.cwe}` : ""}
            </p>
          </div>
          {finding.snippet ? (
            <SnippetView
              snippet={finding.snippet}
              lineStart={finding.line_start}
              lineEnd={finding.line_end}
            />
          ) : (
            <p className="fine-print">No source snippet is available for this finding.</p>
          )}
          <ExplanationPanel findingId={finding.id} />
        </div>
      )}
    </li>
  );
}
