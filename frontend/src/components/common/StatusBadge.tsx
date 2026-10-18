import type { ScannerStatus } from "../../types/finding";

const TONE: Record<ScannerStatus, string> = {
  completed: "pill-ok",
  partial: "pill-warn",
  skipped: "pill-idle",
  unavailable: "pill-idle",
  failed: "pill-bad",
  timed_out: "pill-bad",
};

interface StatusBadgeProps {
  status: ScannerStatus;
  label?: string;
}

export default function StatusBadge({ status, label }: StatusBadgeProps) {
  return (
    <span className={`pill ${TONE[status]}`}>
      {label ? `${label}: ` : ""}
      {status.replace("_", " ")}
    </span>
  );
}
