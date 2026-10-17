import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import QueryState from "../components/common/QueryState";
import SeverityBadge from "../components/common/SeverityBadge";
import StatusBadge from "../components/common/StatusBadge";
import { useApi } from "../hooks/useApi";
import { fetchScan } from "../services/api";
import { formatBytes, formatDate } from "../services/format";
import { SEVERITY_ORDER } from "../types/finding";

export default function ScanDetails() {
  const { scanId = "" } = useParams();
  const { state, reload } = useApi((signal) => fetchScan(scanId, signal), `scan-${scanId}`);
  return (
    <div>
      <Link to="/" className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900"><ArrowLeft className="h-4 w-4" aria-hidden="true" />All scans</Link>
      <div className="mt-4">
        <QueryState state={state} onRetry={reload}>
          {(scan) => {
            const languages = Object.entries(scan.metadata.languages).map(([name, count]) => `${name} (${count})`).join(", ");
            return <div className="space-y-8">
              <div><h1 className="text-2xl font-semibold">{scan.metadata.archive_name}</h1><p className="mt-1 text-sm text-gray-500">Scanned {formatDate(scan.created_at)}</p></div>
              <section><h2 className="text-lg font-medium">Findings by severity</h2><div className="mt-2 flex flex-wrap gap-2">{SEVERITY_ORDER.map((severity) => <SeverityBadge key={severity} severity={severity} count={scan.severity_counts[severity]} />)}</div><p className="mt-2 text-sm text-gray-600">{scan.findings_total} finding(s) in total.</p></section>
              <section><h2 className="text-lg font-medium">Repository</h2><dl className="mt-2 grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-4"><div><dt className="text-gray-500">Files scanned</dt><dd className="font-medium">{scan.metadata.source_files}</dd></div><div><dt className="text-gray-500">Entries skipped</dt><dd className="font-medium">{scan.metadata.skipped_entries}</dd></div><div><dt className="text-gray-500">Source size</dt><dd className="font-medium">{formatBytes(scan.metadata.total_bytes)}</dd></div><div><dt className="text-gray-500">Languages</dt><dd className="font-medium">{languages || "none"}</dd></div></dl>{scan.metadata.dependency_manifests.length > 0 && <p className="mt-2 text-sm text-gray-600">Dependency manifests: {scan.metadata.dependency_manifests.join(", ")}</p>}</section>
              <section><h2 className="text-lg font-medium">Scanner coverage</h2><div className="mt-2 overflow-x-auto rounded-lg border border-gray-200 bg-white"><table className="min-w-full divide-y divide-gray-200 text-sm"><thead className="bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500"><tr><th className="px-4 py-3">Scanner</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Findings</th><th className="px-4 py-3">Time</th><th className="px-4 py-3">Notes</th></tr></thead><tbody className="divide-y divide-gray-100">{scan.scanner_runs.map((run) => <tr key={run.scanner}><td className="px-4 py-3 align-top font-medium">{run.scanner}{run.version && <span className="ml-1 text-xs font-normal text-gray-500">{run.version}</span>}</td><td className="px-4 py-3 align-top"><StatusBadge status={run.status} /></td><td className="px-4 py-3 align-top">{run.findings_count}</td><td className="px-4 py-3 align-top">{run.duration_seconds}s</td><td className="px-4 py-3 align-top text-gray-600">{run.message ?? ""}</td></tr>)}</tbody></table></div></section>
              <p className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">{scan.notice}</p>
            </div>;
          }}
        </QueryState>
      </div>
    </div>
  );
}
