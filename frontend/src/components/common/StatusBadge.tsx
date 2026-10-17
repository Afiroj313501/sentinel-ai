import type { ScannerStatus } from "../../types/finding";

const STYLES: Record<ScannerStatus, string> = {
  completed: "bg-green-100 text-green-800",
  partial: "bg-amber-100 text-amber-800",
  skipped: "bg-gray-100 text-gray-600",
  unavailable: "bg-gray-100 text-gray-600",
  failed: "bg-red-100 text-red-800",
  timed_out: "bg-red-100 text-red-800",
};

export default function StatusBadge({ status, label }: { status: ScannerStatus; label?: string }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STYLES[status]}`}>
      {label ? `${label}: ` : ""}{status.replace("_", " ")}
    </span>
  );
}
