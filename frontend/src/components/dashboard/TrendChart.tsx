import { formatShortDate } from "../../services/format";
import type { ScanSummary } from "../../types/scan";

export default function TrendChart({ scans }: { scans: ScanSummary[] }) {
  if (scans.length < 2) return <p className="empty">A trend appears after your second scan.</p>;
  const left = 42, right = 605, top = 25, bottom = 185;
  const total = scans.map((scan) => scan.findings_total);
  const serious = scans.map((scan) => scan.severity_counts.high + scan.severity_counts.critical);
  const yMax = Math.max(1, ...total);
  const x = (i: number) => left + (i / (scans.length - 1)) * (right - left);
  const y = (v: number) => bottom - (v / yMax) * (bottom - top);
  const path = (values: number[]) => values.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
  const labels = scans.length <= 6 ? scans.map((_, i) => i) : [0, Math.floor((scans.length - 1) / 2), scans.length - 1];
  return <svg className="chart" viewBox="0 0 630 225" role="img" aria-label="Findings trend">
    <g stroke="var(--line)" strokeDasharray="3 5">{[0, .25, .5, .75, 1].map((v) => <line key={v} x1={left} y1={y(yMax * v)} x2={right} y2={y(yMax * v)} />)}</g>
    {labels.map((i) => <text key={i} x={x(i)} y="211" textAnchor="middle">{formatShortDate(scans[i].created_at)}</text>)}
    <path d={`${path(total)} L${right} ${bottom} L${left} ${bottom}Z`} fill="#4d8dff18" />
    <path d={path(total)} fill="none" stroke="#4d8dff" strokeWidth="2.5" />
    <path d={path(serious)} fill="none" stroke="#fb7185" strokeWidth="2" />
  </svg>;
}
