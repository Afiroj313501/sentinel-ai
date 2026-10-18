import { useState } from "react";
import { Link } from "react-router-dom";
import { Trash2 } from "lucide-react";
import QueryState from "../components/common/QueryState";
import SeverityBadge from "../components/common/SeverityBadge";
import StatusBadge from "../components/common/StatusBadge";
import { useApi } from "../hooks/useApi";
import { deleteScan, fetchScans } from "../services/api";
import { formatDate } from "../services/format";
import { SEVERITY_ORDER } from "../types/finding";
import type { ScanSummary } from "../types/scan";

const PAGE_SIZE = 10;

export default function Dashboard() {
  const [offset, setOffset] = useState(0);
  const [actionError, setActionError] = useState<string | null>(null);
  const { state, reload } = useApi((signal) => fetchScans(PAGE_SIZE, offset, signal), `scans-${offset}`);

  async function handleDelete(scan: ScanSummary, itemsOnPage: number) {
    if (!window.confirm(`Delete the scan of ${scan.archive_name}? This cannot be undone.`)) return;
    try {
      await deleteScan(scan.scan_id);
      setActionError(null);
      if (itemsOnPage === 1 && offset > 0) setOffset(offset - PAGE_SIZE);
      else reload();
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "The scan could not be deleted.");
    }
  }

  return (
    <div className="history-page">
      <section className="welcome">
        <div>
          <div className="eyebrow">SECURITY WORKSPACE</div>
          <h1>Scan history</h1>
          <p>Review repositories previously analyzed by Sentinel and revisit their findings.</p>
        </div>
        <Link to="/new" className="btn btn-primary">New scan</Link>
      </section>

      {actionError && <p role="alert" className="scan-error">{actionError}</p>}
      <QueryState state={state} onRetry={reload}>
        {(page) => page.total === 0 ? (
          <article className="card history-empty">
            <div className="upload-icon"><Trash2 aria-hidden="true" /></div>
            <h2>No scans yet</h2>
            <p>Upload a repository to create your first security scan.</p>
            <Link to="/new" className="btn btn-primary">Start your first scan</Link>
          </article>
        ) : (
          <article className="card history-card">
            <div className="panel-head">
              <div>
                <div className="panel-title">Repository scans</div>
                <div className="panel-sub">{page.total} scan{page.total === 1 ? "" : "s"} in your workspace</div>
              </div>
              <span className="history-count">{offset + 1}-{Math.min(offset + page.items.length, page.total)} of {page.total}</span>
            </div>
            <div className="history-table-wrap">
              <table className="history-table">
                <thead><tr><th>Repository</th><th>Findings</th><th>Scanners</th><th><span className="sr-only">Actions</span></th></tr></thead>
                <tbody>
                  {page.items.map((scan) => (
                    <tr key={scan.scan_id}>
                      <td className="history-repository">
                        <Link to={`/scans/${scan.scan_id}`}>{scan.archive_name}</Link>
                        <span>{formatDate(scan.created_at)} · {scan.source_files} files</span>
                      </td>
                      <td>
                        <div className="history-badges">
                          {SEVERITY_ORDER.filter((severity) => scan.severity_counts[severity] > 0).map((severity) => <SeverityBadge key={severity} severity={severity} count={scan.severity_counts[severity]} />)}
                        </div>
                        <span className="history-total">{scan.findings_total} total</span>
                      </td>
                      <td><div className="history-badges">{Object.entries(scan.scanner_statuses).map(([scanner, status]) => <StatusBadge key={scanner} status={status} label={scanner} />)}</div></td>
                      <td className="history-action"><button type="button" title={`Delete ${scan.archive_name}`} onClick={() => handleDelete(scan, page.items.length)}><Trash2 aria-hidden="true" /></button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="history-footer">
              <span>{offset + 1}-{Math.min(offset + page.items.length, page.total)} of {page.total}</span>
              <div><button type="button" className="btn btn-ghost" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>Previous</button><button type="button" className="btn btn-ghost" disabled={offset + PAGE_SIZE >= page.total} onClick={() => setOffset(offset + PAGE_SIZE)}>Next</button></div>
            </div>
          </article>
        )}
      </QueryState>
    </div>
  );
}
