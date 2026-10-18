import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useApi } from "../../hooks/useApi";
import { fetchFindings } from "../../services/api";
import type { Severity } from "../../types/finding";
import type { ScanSummary } from "../../types/scan";

type Tab = "all" | Severity;
const tabs: { key: Tab; label: string }[] = [{ key: "all", label: "All findings" }, { key: "critical", label: "Critical" }, { key: "high", label: "High" }, { key: "medium", label: "Medium" }, { key: "low", label: "Low" }];
export default function RecentFindings({ scan }: { scan: ScanSummary }) {
  const [tab, setTab] = useState<Tab>("all");
  const navigate = useNavigate();
  const { state, reload } = useApi((signal) => fetchFindings(scan.scan_id, { severity: tab === "all" ? [] : [tab], category: [], scanner: [], q: "", filePath: "", limit: 5, offset: 0 }, signal), `recent-${scan.scan_id}-${tab}`);
  return <article className="card findings"><div className="panel-head"><div><div className="panel-title">Recent security findings</div><div className="panel-sub">Most severe findings from your latest scan</div></div><Link to={`/scans/${scan.scan_id}`} className="text-btn">View all →</Link></div><div className="tabs" role="tablist">{tabs.map(({ key, label }) => <button key={key} type="button" role="tab" aria-selected={tab === key} className={`tab${tab === key ? " active" : ""}`} onClick={() => setTab(key)}>{label} <span>{key === "all" ? scan.findings_total : scan.severity_counts[key]}</span></button>)}</div>{state.status === "loading" && <p className="empty">Loading findings...</p>}{state.status === "error" && <div className="empty" role="alert">{state.message} <button type="button" className="text-btn" onClick={reload}>Try again</button></div>}{state.status === "success" && (state.data.items.length === 0 ? <p className="empty">No findings in this category.</p> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Finding</th><th>Severity</th><th>Scanner</th><th>Confidence</th></tr></thead><tbody>{state.data.items.map((finding) => <tr key={finding.id} onClick={() => navigate(`/scans/${scan.scan_id}`)}><td><Link to={`/scans/${scan.scan_id}`} className="finding-name">{finding.title}</Link><div className="finding-file">{finding.file_path}:{finding.line_start}</div></td><td><span className={`severity sev-${finding.severity}`}>{finding.severity}</span></td><td>{finding.scanner} · {finding.rule_id}</td><td>{finding.confidence}</td></tr>)}</tbody></table></div>)}</article>;
}
