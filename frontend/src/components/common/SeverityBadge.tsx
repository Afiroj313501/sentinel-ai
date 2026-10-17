import type { Severity } from "../../types/finding";

const STYLES: Record<Severity, string> = {
  critical: "bg-red-900 text-white",
  high: "bg-red-100 text-red-800",
  medium: "bg-amber-100 text-amber-800",
  low: "bg-blue-100 text-blue-800",
  info: "bg-gray-100 text-gray-700",
};

export default function SeverityBadge({ severity, count }: { severity: Severity; count?: number }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STYLES[severity]}`}>
      {severity}{count !== undefined && `: ${count}`}
    </span>
  );
}
