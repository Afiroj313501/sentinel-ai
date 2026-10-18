export interface FixSuggestion {
  finding_id: string;
  file_path: string;
  can_fix: boolean;
  rationale: string;
  diff: string | null;
  syntax_check: "passed" | "not_checked";
  provider: string;
  model: string;
  created_at: string;
  tested: false;
  requires_human_review: true;
  notice: string;
}
