import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import QueryState from "../components/common/QueryState";
import SeverityBadge from "../components/common/SeverityBadge";
import StatusBadge from "../components/common/StatusBadge";
import FindingsSection from "../components/findings/FindingsSection";
import { useApi } from "../hooks/useApi";
import { fetchScan } from "../services/api";
import { formatBytes, formatDate } from "../services/format";
import { SEVERITY_ORDER } from "../types/finding";

export default function ScanDetails() {
  const { scanId = "" } = useParams();
  const { state, reload } = useApi((signal) => fetchScan(scanId, signal), `scan-${scanId}`);

  return (
    <div>
      <Link to="/history" className="back-link">
        <ArrowLeft size={14} aria-hidden="true" />
        All scans
      </Link>

      <QueryState state={state} onRetry={reload}>
        {(scan) => {
          const languages = Object.entries(scan.metadata.languages)
            .map(([name, count]) => `${name} (${count})`)
            .join(", ");
          return (
            <div className="stack">
              <section className="welcome" style={{ marginBottom: 8 }}>
                <div>
                  <div className="eyebrow">SCAN DETAILS</div>
                  <h1>{scan.metadata.archive_name}</h1>
                  <p>Scanned {formatDate(scan.created_at)}</p>
                </div>
              </section>

              <article className="card">
                <div className="panel-head">
                  <div>
                    <div className="panel-title">Findings by severity</div>
                    <div className="panel-sub">{scan.findings_total} finding(s) in total</div>
                  </div>
                </div>
                <div className="card-body chips">
                  {SEVERITY_ORDER.map((severity) => (
                    <SeverityBadge key={severity} severity={severity} count={scan.severity_counts[severity]} />
                  ))}
                </div>
              </article>

              <article className="card">
                <div className="panel-head">
                  <div>
                    <div className="panel-title">Repository</div>
                    <div className="panel-sub">What was extracted and analyzed</div>
                  </div>
                </div>
                <dl className="facts">
                  <div>
                    <dt>Files scanned</dt>
                    <dd>{scan.metadata.source_files}</dd>
                  </div>
                  <div>
                    <dt>Entries skipped</dt>
                    <dd>{scan.metadata.skipped_entries}</dd>
                  </div>
                  <div>
                    <dt>Source size</dt>
                    <dd>{formatBytes(scan.metadata.total_bytes)}</dd>
                  </div>
                  <div>
                    <dt>Languages</dt>
                    <dd>{languages || "none"}</dd>
                  </div>
                </dl>
                {scan.metadata.dependency_manifests.length > 0 && (
                  <p className="card-body small muted" style={{ margin: 0 }}>
                    Dependency manifests: {scan.metadata.dependency_manifests.join(", ")}
                  </p>
                )}
              </article>

              <article className="card">
                <div className="panel-head">
                  <div>
                    <div className="panel-title">Scanner coverage</div>
                    <div className="panel-sub">Which tools actually ran on this repository</div>
                  </div>
                </div>
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Scanner</th>
                        <th>Status</th>
                        <th>Findings</th>
                        <th>Time</th>
                        <th>Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {scan.scanner_runs.map((run) => (
                        <tr key={run.scanner} style={{ cursor: "default" }}>
                          <td>
                            <span className="finding-name">{run.scanner}</span>
                            {run.version && <div className="finding-file">{run.version}</div>}
                          </td>
                          <td>
                            <StatusBadge status={run.status} />
                          </td>
                          <td>{run.findings_count}</td>
                          <td>{run.duration_seconds}s</td>
                          <td className="muted">{run.message ?? ""}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </article>

              <p className="alert alert-warn">{scan.notice}</p>

              <FindingsSection scanId={scanId} scanners={scan.scanner_runs.map((run) => run.scanner)} />
            </div>
          );
        }}
      </QueryState>
    </div>
  );
}
