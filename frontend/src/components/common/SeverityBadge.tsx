import type { Severity } from "../../types/finding";

const STYLES: Record<Severity, string> = {
  critical: "severity-chip sev-critical",
  high: "severity-chip sev-high",
  medium: "severity-chip sev-medium",
  low: "severity-chip sev-low",
  info: "severity-chip sev-info",
};

export default function SeverityBadge({ severity, count }: { severity: Severity; count?: number }) {
  return (
    <span className={STYLES[severity]}>
      {severity}{count !== undefined && `: ${count}`}
    </span>
  );
}
