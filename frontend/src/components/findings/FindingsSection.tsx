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

function toggle<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
}

function FilterGroup({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="filter-row">
      <span className="filter-label">{label}</span>
      {children}
    </div>
  );
}

interface FindingsSectionProps {
  scanId: string;
  scanners: string[];
}

export default function FindingsSection({ scanId, scanners }: FindingsSectionProps) {
  const [severity, setSeverity] = useState<Severity[]>([]);
  const [category, setCategory] = useState<Category[]>([]);
  const [scannerFilter, setScannerFilter] = useState<string[]>([]);
  const [search, setSearch] = useState("");
  const [filePath, setFilePath] = useState("");
  const [offset, setOffset] = useState(0);

  const debouncedSearch = useDebouncedValue(search.trim(), 300);
  const debouncedFilePath = useDebouncedValue(filePath.trim(), 300);

  const query: FindingsQuery = {
    severity,
    category,
    scanner: scannerFilter,
    q: debouncedSearch,
    filePath: debouncedFilePath,
    limit: PAGE_SIZE,
    offset,
  };
  const { state, reload } = useApi(
    (signal) => fetchFindings(scanId, query, signal),
    `findings-${scanId}-${JSON.stringify(query)}`,
  );

  const filtersActive =
    severity.length > 0 ||
    category.length > 0 ||
    scannerFilter.length > 0 ||
    search !== "" ||
    filePath !== "";

  // Any filter change returns to the first page.
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
    <article className="card">
      <div className="panel-head">
        <div>
          <div className="panel-title">Findings</div>
          <div className="panel-sub">Scanner evidence, with optional AI help on each finding</div>
        </div>
      </div>

      <div className="filters">
        <FilterGroup label="Severity">
          {SEVERITY_ORDER.map((value) => (
            <FilterChip
              key={value}
              label={value}
              active={severity.includes(value)}
              onToggle={() => change(setSeverity, toggle(severity, value))}
            />
          ))}
        </FilterGroup>
        <FilterGroup label="Category">
          {CATEGORIES.map((value) => (
            <FilterChip
              key={value}
              label={value}
              active={category.includes(value)}
              onToggle={() => change(setCategory, toggle(category, value))}
            />
          ))}
        </FilterGroup>
        <FilterGroup label="Scanner">
          {scanners.map((value) => (
            <FilterChip
              key={value}
              label={value}
              active={scannerFilter.includes(value)}
              onToggle={() => change(setScannerFilter, toggle(scannerFilter, value))}
            />
          ))}
        </FilterGroup>

        <div className="filter-inputs">
          <label className="input-wrap">
            <span className="sr-only">Search findings</span>
            <Search aria-hidden="true" />
            <input
              type="search"
              className="input"
              value={search}
              maxLength={100}
              onChange={(event) => change(setSearch, event.target.value)}
              placeholder="Search title, evidence, or rule"
            />
          </label>
          <label className="input-wrap">
            <span className="sr-only">Filter by file path</span>
            <Search aria-hidden="true" />
            <input
              type="search"
              className="input"
              value={filePath}
              maxLength={300}
              onChange={(event) => change(setFilePath, event.target.value)}
              placeholder="File path contains..."
            />
          </label>
        </div>

        {filtersActive && (
          <div>
            <button type="button" className="text-btn" onClick={clearFilters}>
              <X size={13} aria-hidden="true" style={{ display: "inline", marginRight: 4 }} />
              Clear filters
            </button>
          </div>
        )}
      </div>

      <QueryState state={state} onRetry={reload}>
        {(page) =>
          page.total === 0 ? (
            <p className="empty">
              {filtersActive
                ? "No findings match these filters."
                : "The scanners that ran reported no findings. This does not prove the code is secure; check the scanner coverage table above."}
            </p>
          ) : (
            <>
              <p className="results-count">
                Showing {page.offset + 1}-{page.offset + page.items.length} of {page.total}
              </p>
              <ul className="finding-list">
                {page.items.map((finding) => (
                  <FindingCard key={finding.id} finding={finding} />
                ))}
              </ul>
              <div className="pager inset">
                <span />
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
    </article>
  );
}
