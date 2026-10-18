import type { ReactNode } from "react";

export default function StatCard({ label, value, icon, tone, footer, spark }: {
  label: string; value: ReactNode; icon: ReactNode; tone: "blue" | "red" | "amber" | "green"; footer: ReactNode; spark?: ReactNode;
}) {
  return <article className="card stat"><div className="stat-head">{label}<span className={`stat-icon i-${tone}`}>{icon}</span></div><div className="stat-value">{value}</div><div className="stat-bottom">{footer}</div>{spark}</article>;
}
