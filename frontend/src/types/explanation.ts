import type { Confidence } from "./finding";

export interface Explanation {
  finding_id: string;
  provider: string;
  model: string;
  created_at: string;
  summary: string;
  impact: string;
  confidence: Exclude<Confidence, "unknown">;
  remediation: string;
  evidence_sufficient: boolean;
  notice: string;
}
