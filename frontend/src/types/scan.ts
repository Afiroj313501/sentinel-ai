import type {
  Category,
  Finding,
  RepositoryMetadata,
  ScannerRun,
  ScannerStatus,
  Severity,
  SeverityCounts,
} from "./finding";

export interface ScanSummary {
  scan_id: string;
  archive_name: string;
  created_at: string;
  source_files: number;
  findings_total: number;
  severity_counts: SeverityCounts;
  scanner_statuses: Record<string, ScannerStatus>;
}

export interface ScanListPage {
  total: number;
  limit: number;
  offset: number;
  items: ScanSummary[];
}

export interface ScanDetail {
  metadata: RepositoryMetadata;
  created_at: string;
  scanner_runs: ScannerRun[];
  severity_counts: SeverityCounts;
  findings_total: number;
  notice: string;
}

export interface FindingsPage {
  total: number;
  limit: number;
  offset: number;
  items: Finding[];
}

export interface FindingsQuery {
  severity: Severity[];
  category: Category[];
  scanner: string[];
  q: string;
  filePath: string;
  limit: number;
  offset: number;
}
