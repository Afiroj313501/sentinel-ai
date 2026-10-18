import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Trash2 } from "lucide-react";
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
  const { state, reload } = useApi(
    (signal) => fetchScans(PAGE_SIZE, offset, signal),
    `scans-${offset}`,
  );

  async function handleDelete(scan: ScanSummary, itemsOnPage: number) {
    if (!window.confirm(`Delete the scan of ${scan.archive_name}? This cannot be undone.`)) return;
    try {
      await deleteScan(scan.scan_id);
      setActionError(null);
      if (itemsOnPage === 1 && offset > 0) {
        setOffset(offset - PAGE_SIZE);
      } else {
        reload();
      }
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "The scan could not be deleted.");
    }
  }

  return (
    <div>
      <section className="welcome">
        <div>
          <div className="eyebrow">SCAN HISTORY</div>
          <h1>Scan history</h1>
          <p>Every scan stored by this backend, newest first.</p>
        </div>
        <div className="welcome-actions">
          <Link to="/new" className="btn btn-primary">
            <Plus aria-hidden="true" />
            Run new scan
          </Link>
        </div>
      </section>

      {actionError && (
        <p role="alert" className="alert alert-error" style={{ marginBottom: 16 }}>
          {actionError}
        </p>
      )}

      <QueryState state={state} onRetry={reload}>
        {(page) =>
          page.total === 0 ? (
            <article className="card">
              <p className="empty">
                No scans yet.{" "}
                <Link to="/new" className="text-btn">
                  Start your first scan â†’
                </Link>
              </p>
            </article>
          ) : (
            <>
              <article className="card">
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Repository</th>
                        <th>Findings</th>
                        <th>Scanners</th>
                        <th>
                          <span className="sr-only">Actions</span>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {page.items.map((scan) => (
                        <tr key={scan.scan_id} style={{ cursor: "default" }}>
                          <td>
                            <Link to={`/scans/${scan.scan_id}`} className="finding-name">
                              {scan.archive_name}
                            </Link>
                            <div className="finding-file">
                              {formatDate(scan.created_at)} Â· {scan.source_files} files
                            </div>
                          </td>
                          <td>
                            <div className="chips">
                              {SEVERITY_ORDER.filter((s) => scan.severity_counts[s] > 0).map((s) => (
                                <SeverityBadge key={s} severity={s} count={scan.severity_counts[s]} />
                              ))}
                              {scan.findings_total === 0 && <span className="status">None reported</span>}
                            </div>
                          </td>
                          <td>
                            <div className="chips">
                              {Object.entries(scan.scanner_statuses).map(([name, status]) => (
                                <StatusBadge key={name} label={name} status={status} />
                              ))}
                            </div>
                          </td>
                          <td style={{ textAlign: "right" }}>
                            <button
                              type="button"
                              className="icon-btn"
                              onClick={() => void handleDelete(scan, page.items.length)}
                              aria-label={`Delete scan of ${scan.archive_name}`}
                            >
                              <Trash2 size={15} aria-hidden="true" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </article>

              <div className="pager">
                <span>
                  Showing {page.offset + 1}-{page.offset + page.items.length} of {page.total}
                </span>
                <div>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    disabled={offset === 0}
                    onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                  >
                    Previous
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    disabled={offset + PAGE_SIZE >= page.total}
                    onClick={() => setOffset(offset + PAGE_SIZE)}
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )
        }
      </QueryState>
    </div>
  );
}
