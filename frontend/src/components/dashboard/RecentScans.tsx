import { Link } from "react-router-dom";
import { formatRelative } from "../../services/format";
import type { ScanSummary } from "../../types/scan";

export default function RecentScans({ scans, total }: { scans: ScanSummary[]; total: number }) {
  return <article className="card"><div className="panel-head"><div><div className="panel-title">Recent activity</div><div className="panel-sub">Latest repository scans</div></div></div><div className="activity">{scans.map((scan) => { const statuses = Object.values(scan.scanner_statuses); const ran = statuses.filter((s) => s === "completed" || s === "partial").length; return <div className="activity-row" key={scan.scan_id}><Link to={`/scans/${scan.scan_id}`}>{scan.archive_name}</Link><div className="repo-line"><span className="status-dot" style={{ background: ran === statuses.length ? "var(--green)" : "var(--amber)" }} />{scan.findings_total} finding(s) · {ran} of {statuses.length} scanners ran</div><time>{formatRelative(scan.created_at)}</time></div>; })}</div><div style={{ padding: "0 19px 17px" }}><Link to="/history" className="btn btn-ghost btn-block">View all {total} scans →</Link></div></article>;
}
