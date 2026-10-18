import { SEVERITY_ORDER } from "../../types/finding";
import type { Severity, SeverityCounts } from "../../types/finding";

const COLORS: Record<Severity, string> = { critical: "#fb7185", high: "#fb923c", medium: "#fbbf24", low: "#60a5fa", info: "#94a3b8" };
export default function SeverityDonut({ counts }: { counts: SeverityCounts }) {
  const total = SEVERITY_ORDER.reduce((sum, severity) => sum + counts[severity], 0);
  const circumference = 2 * Math.PI * 65;
  const segments = SEVERITY_ORDER.filter((s) => counts[s] > 0).reduce<{ severity: Severity; length: number; offset: number }[]>((items, severity) => {
    const length = total ? counts[severity] / total * circumference : 0;
    const offset = (items.at(-1)?.offset ?? 0) + (items.at(-1)?.length ?? 0);
    return [...items, { severity, length, offset }];
  }, []);
  return <div className="score-body"><div className="score-ring" role="img" aria-label={`${total} findings`}><svg viewBox="0 0 160 160" aria-hidden="true"><circle cx="80" cy="80" r="65" stroke="var(--line)" strokeWidth="12" fill="none" />{segments.map((segment) => <circle key={segment.severity} cx="80" cy="80" r="65" stroke={COLORS[segment.severity]} strokeWidth="12" fill="none" strokeDasharray={`${segment.length} ${circumference - segment.length}`} strokeDashoffset={-segment.offset} />)}</svg><div className="score-copy"><strong>{total}</strong><span>FINDINGS</span></div></div><div className="score-details">{SEVERITY_ORDER.map((severity) => <div key={severity} className="score-item"><i style={{ background: COLORS[severity] }} /><div><strong>{counts[severity]}</strong><span>{severity}</span></div></div>)}</div></div>;
}
