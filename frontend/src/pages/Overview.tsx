import { Link } from "react-router-dom";
import { AlertTriangle, FileSearch, Plus, ShieldAlert, ShieldCheck } from "lucide-react";
import QueryState from "../components/common/QueryState";
import RecentFindings from "../components/dashboard/RecentFindings";
import RecentScans from "../components/dashboard/RecentScans";
import SeverityDonut from "../components/dashboard/SeverityDonut";
import Sparkline from "../components/dashboard/Sparkline";
import StatCard from "../components/dashboard/StatCard";
import TrendChart from "../components/dashboard/TrendChart";
import { useApi } from "../hooks/useApi";
import { fetchScan, fetchScans } from "../services/api";
import { formatRelative } from "../services/format";
import type { ScanListPage, ScanSummary } from "../types/scan";

const seriousCount = (scan: ScanSummary) => scan.severity_counts.critical + scan.severity_counts.high;
function changeFooter(current: number, previous: number | undefined) {
  if (previous === undefined) return <span>First scan on record</span>;
  const diff = current - previous;
  return diff === 0 ? <span>No change vs previous scan</span> : <><span className={diff < 0 ? "trend" : "trend up"}>{diff < 0 ? "↓" : "↑"} {Math.abs(diff)}</span><span>vs previous scan</span></>;
}

function OverviewBody({ page }: { page: ScanListPage }) {
  const latest = page.items[0], previous = page.items[1], chronological = [...page.items].reverse();
  const statuses = Object.values(latest.scanner_statuses);
  const ran = statuses.filter((s) => s === "completed" || s === "partial").length;
  const serious = seriousCount(latest);
  const detail = useApi((signal) => fetchScan(latest.scan_id, signal), `overview-detail-${latest.scan_id}`);
  return <>
    <section className="dash-grid stats" aria-label="Summary">
      <StatCard label="Scans run" value={page.total} tone="blue" icon={<FileSearch aria-hidden="true" />} footer={<span>Latest {formatRelative(latest.created_at)}</span>} />
      <StatCard label="Findings (latest scan)" value={latest.findings_total} tone="red" icon={<ShieldAlert aria-hidden="true" />} footer={changeFooter(latest.findings_total, previous?.findings_total)} spark={<Sparkline values={chronological.map((s) => s.findings_total)} color="#fb7185" />} />
      <StatCard label="High and critical" value={serious} tone="amber" icon={<AlertTriangle aria-hidden="true" />} footer={<><span style={{ color: serious ? "var(--amber)" : "var(--green)", fontWeight: 750 }}>{serious ? "Needs attention" : "None reported"}</span><span>{latest.archive_name}</span></>} spark={<Sparkline values={chronological.map(seriousCount)} color="#fbbf24" />} />
      <StatCard label="Scanners that ran" value={`${ran}/${statuses.length}`} tone={ran === statuses.length ? "green" : "amber"} icon={<ShieldCheck aria-hidden="true" />} footer={<span>{ran === statuses.length ? "All scanners ran" : `${statuses.length - ran} did not run`}</span>} />
    </section>
    <section className="dash-grid main-grid"><article className="card"><div className="panel-head"><div><div className="panel-title">Security overview</div><div className="panel-sub">Findings per scan across your last {chronological.length} scan(s)</div></div></div><div className="chart-wrap"><TrendChart scans={chronological} /></div>{chronological.length >= 2 && <div className="legend"><span><i style={{ background: "#4d8dff" }} />All findings</span><span><i style={{ background: "#fb7185" }} />High and critical</span></div>}</article><article className="card score-card"><div className="panel-head"><div><div className="panel-title">Severity breakdown</div><div className="panel-sub">{latest.archive_name}</div></div></div><SeverityDonut counts={latest.severity_counts} />{detail.state.status === "success" && <p className="score-note">{detail.state.data.notice}</p>}</article></section>
    <section className="dash-grid bottom-grid"><RecentFindings scan={latest} /><RecentScans scans={page.items.slice(0, 4)} total={page.total} /></section>
  </>;
}

export default function Overview() {
  const { state, reload } = useApi((signal) => fetchScans(12, 0, signal), "overview-scans");
  return <div><section className="welcome"><div><div className="eyebrow">SECURITY COMMAND CENTER</div><h1>Overview</h1><p>Here is what the scanners found across your uploaded repositories.</p></div><div className="welcome-actions"><Link to="/new" className="btn btn-primary"><Plus aria-hidden="true" />Run new scan</Link></div></section><QueryState state={state} onRetry={reload}>{(page) => page.total === 0 ? <article className="card"><p className="empty">No scans yet. <Link to="/new" className="text-btn">Run your first scan →</Link></p></article> : <OverviewBody page={page} />}</QueryState><div className="page-foot">Sentinel AI · Findings come from deterministic scanners; AI text is labeled separately.</div></div>;
}
