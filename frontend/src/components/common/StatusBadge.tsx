import type { ScannerStatus } from "../../types/finding";

const STYLES: Record<ScannerStatus, string> = {
  completed: "status-chip status-completed",
  partial: "status-chip status-partial",
  skipped: "status-chip status-muted",
  unavailable: "status-chip status-muted",
  failed: "status-chip status-failed",
  timed_out: "status-chip status-failed",
};

export default function StatusBadge({ status, label }: { status: ScannerStatus; label?: string }) {
  return (
    <span className={STYLES[status]}>
      {label ? `${label}: ` : ""}{status.replace("_", " ")}
    </span>
  );
}
