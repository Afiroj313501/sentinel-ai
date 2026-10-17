import { useState } from "react";
import type { ReactNode } from "react";
import { Search, X } from "lucide-react";
import FilterChip from "../common/FilterChip";
import QueryState from "../common/QueryState";
import FindingCard from "./FindingCard";
import { useApi } from "../../hooks/useApi";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { fetchFindings } from "../../services/api";
import { SEVERITY_ORDER } from "../../types/finding";
import type { Category, Severity } from "../../types/finding";
import type { FindingsQuery } from "../../types/scan";

const PAGE_SIZE = 20;
const CATEGORIES: readonly Category[] = ["security", "bug", "quality"];
const INPUT = "w-full rounded-md border border-gray-300 py-1.5 pl-8 pr-3 text-sm placeholder:text-gray-400 focus:border-indigo-500 focus:outline-none";
const BUTTON = "rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50";

function toggle<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
}

function FilterGroup({ label, children }: { label: string; children: ReactNode }) {
  return <div className="flex flex-wrap items-center gap-2"><span className="w-20 text-xs font-medium uppercase tracking-wide text-gray-500">{label}</span>{children}</div>;
}

export default function FindingsSection({ scanId, scanners }: { scanId: string; scanners: string[] }) {
  const [severity, setSeverity] = useState<Severity[]>([]);
  const [category, setCategory] = useState<Category[]>([]);
  const [scannerFilter, setScannerFilter] = useState<string[]>([]);
  const [search, setSearch] = useState("");
  const [filePath, setFilePath] = useState("");
  const [offset, setOffset] = useState(0);
  const debouncedSearch = useDebouncedValue(search.trim(), 300);
  const debouncedFilePath = useDebouncedValue(filePath.trim(), 300);
  const query: FindingsQuery = { severity, category, scanner: scannerFilter, q: debouncedSearch, filePath: debouncedFilePath, limit: PAGE_SIZE, offset };
  const { state, reload } = useApi((signal) => fetchFindings(scanId, query, signal), `findings-${scanId}-${JSON.stringify(query)}`);
  const filtersActive = severity.length > 0 || category.length > 0 || scannerFilter.length > 0 || search !== "" || filePath !== "";

  function change<T>(setter: (value: T) => void, value: T) {
    setter(value);
    setOffset(0);
  }

  function clearFilters() {
    setSeverity([]);
    setCategory([]);
    setScannerFilter([]);
    setSearch("");
    setFilePath("");
    setOffset(0);
  }

  return (
    <section>
      <h2 className="text-lg font-medium">Findings</h2>
      <div className="mt-3 space-y-3 rounded-lg border border-gray-200 bg-white p-4">
        <FilterGroup label="Severity">{SEVERITY_ORDER.map((value) => <FilterChip key={value} label={value} active={severity.includes(value)} onToggle={() => change(setSeverity, toggle(severity, value))} />)}</FilterGroup>
        <FilterGroup label="Category">{CATEGORIES.map((value) => <FilterChip key={value} label={value} active={category.includes(value)} onToggle={() => change(setCategory, toggle(category, value))} />)}</FilterGroup>
        <FilterGroup label="Scanner">{scanners.map((value) => <FilterChip key={value} label={value} active={scannerFilter.includes(value)} onToggle={() => change(setScannerFilter, toggle(scannerFilter, value))} />)}</FilterGroup>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="relative block"><span className="sr-only">Search findings</span><Search className="pointer-events-none absolute left-2.5 top-2 h-4 w-4 text-gray-400" aria-hidden="true" /><input type="search" value={search} maxLength={100} onChange={(event) => change(setSearch, event.target.value)} placeholder="Search title, evidence, or rule" className={INPUT} /></label>
          <label className="relative block"><span className="sr-only">Filter by file path</span><Search className="pointer-events-none absolute left-2.5 top-2 h-4 w-4 text-gray-400" aria-hidden="true" /><input type="search" value={filePath} maxLength={300} onChange={(event) => change(setFilePath, event.target.value)} placeholder="File path contains..." className={INPUT} /></label>
        </div>
        {filtersActive && <button type="button" onClick={clearFilters} className="inline-flex items-center gap-1 text-sm font-medium text-indigo-700 hover:underline"><X className="h-4 w-4" aria-hidden="true" />Clear filters</button>}
      </div>
      <div className="mt-4">
        <QueryState state={state} onRetry={reload}>
          {(page) => page.total === 0 ? (
            <p className="rounded-lg border border-dashed border-gray-300 p-6 text-center text-sm text-gray-600">{filtersActive ? "No findings match these filters." : "The scanners that ran reported no findings. This does not prove the code is secure; check the scanner coverage table above."}</p>
          ) : (
            <>
              <p className="mb-2 text-sm text-gray-600">Showing {page.offset + 1}-{page.offset + page.items.length} of {page.total}</p>
              <ul className="space-y-2">{page.items.map((finding) => <FindingCard key={finding.id} finding={finding} />)}</ul>
              <div className="mt-4 flex justify-end gap-2"><button type="button" className={BUTTON} disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>Previous</button><button type="button" className={BUTTON} disabled={offset + PAGE_SIZE >= page.total} onClick={() => setOffset(offset + PAGE_SIZE)}>Next</button></div>
            </>
          )}
        </QueryState>
      </div>
    </section>
  );
}
