export type Severity = "critical" | "high" | "medium" | "low" | "info";
export type Confidence = "high" | "medium" | "low" | "unknown";
export type Category = "security" | "bug" | "quality";
export type ScannerStatus =
  | "completed"
  | "partial"
  | "skipped"
  | "unavailable"
  | "failed"
  | "timed_out";

export const SEVERITY_ORDER: readonly Severity[] = ["critical", "high", "medium", "low", "info"];
export type SeverityCounts = Record<Severity, number>;

export interface Finding {
  id: string;
  scan_id: string;
  scanner: string;
  rule_id: string;
  title: string;
  severity: Severity;
  confidence: Confidence;
  category: Category;
  file_path: string;
  line_start: number;
  line_end: number;
  evidence: string;
  snippet: string | null;
  cwe: string | null;
  source: "static-analysis";
}

export interface ScannerRun {
  scanner: string;
  status: ScannerStatus;
  version: string | null;
  findings_count: number;
  duration_seconds: number;
  message: string | null;
}

export interface RepositoryMetadata {
  scan_id: string;
  archive_name: string;
  source_files: number;
  skipped_entries: number;
  total_bytes: number;
  languages: Record<string, number>;
  dependency_manifests: string[];
}

export interface ScanResult {
  metadata: RepositoryMetadata;
  scanner_runs: ScannerRun[];
  findings: Finding[];
  severity_counts: SeverityCounts;
  notice: string;
}
