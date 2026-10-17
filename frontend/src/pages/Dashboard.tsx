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
const BUTTON = "rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50";

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
    <div>
      <div className="flex items-center justify-between"><h1 className="text-2xl font-semibold">Scan history</h1><Link to="/new" className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">New scan</Link></div>
      {actionError && <p role="alert" className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">{actionError}</p>}
      <div className="mt-6">
        <QueryState state={state} onRetry={reload}>
          {(page) => page.total === 0 ? (
            <p className="rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-600">No scans yet. <Link to="/new" className="font-medium text-indigo-700 underline">Start your first scan</Link>.</p>
          ) : (
            <>
              <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500"><tr><th className="px-4 py-3">Repository</th><th className="px-4 py-3">Findings</th><th className="px-4 py-3">Scanners</th><th className="px-4 py-3"><span className="sr-only">Actions</span></th></tr></thead>
                  <tbody className="divide-y divide-gray-100">
                    {page.items.map((scan) => (
                      <tr key={scan.scan_id}>
                        <td className="px-4 py-3 align-top"><Link to={`/scans/${scan.scan_id}`} className="font-medium text-indigo-700 hover:underline">{scan.archive_name}</Link><div className="text-xs text-gray-500">{formatDate(scan.created_at)} · {scan.source_files} files</div></td>
                        <td className="px-4 py-3 align-top"><div className="flex flex-wrap gap-1">{SEVERITY_ORDER.filter((severity) => scan.severity_counts[severity] > 0).map((severity) => <SeverityBadge key={severity} severity={severity} count={scan.severity_counts[severity]} />)}</div><div className="mt-1 text-xs text-gray-500">{scan.findings_total} total</div></td>
                        <td className="px-4 py-3 align-top"><div className="flex flex-wrap gap-1">{Object.entries(scan.scanner_statuses).map(([scanner, status]) => <StatusBadge key={scanner} status={status} label={scanner} />)}</div></td>
                        <td className="px-4 py-3 text-right align-top"><button type="button" title={`Delete ${scan.archive_name}`} onClick={() => handleDelete(scan, page.items.length)} className="text-gray-500 hover:text-red-700"><Trash2 className="h-4 w-4" aria-hidden="true" /></button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-4 flex items-center justify-between text-sm text-gray-600"><span>{offset + 1}-{Math.min(offset + page.items.length, page.total)} of {page.total}</span><div className="flex gap-2"><button type="button" className={BUTTON} disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>Previous</button><button type="button" className={BUTTON} disabled={offset + PAGE_SIZE >= page.total} onClick={() => setOffset(offset + PAGE_SIZE)}>Next</button></div></div>
            </>
          )}
        </QueryState>
      </div>
    </div>
  );
}
