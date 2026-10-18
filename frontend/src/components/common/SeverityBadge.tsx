import type { Severity } from "../../types/finding";

interface SeverityBadgeProps {
  severity: Severity;
  count?: number;
}

export default function SeverityBadge({ severity, count }: SeverityBadgeProps) {
  return (
    <span className={`severity sev-${severity}`}>
      {severity}
      {count !== undefined && `: ${count}`}
    </span>
  );
}
