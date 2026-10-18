export default function Sparkline({ values, color }: { values: number[]; color: string }) {
  if (values.length < 2) return null;
  const max = Math.max(...values), min = Math.min(...values), span = max - min || 1;
  const points = values.map((value, index) => `${(1 + (index / (values.length - 1)) * 78).toFixed(1)} ${(26 - ((value - min) / span) * 24).toFixed(1)}`);
  return <svg className="spark" viewBox="0 0 80 28" aria-hidden="true"><path d={`M${points.join(" L")}`} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" /></svg>;
}
