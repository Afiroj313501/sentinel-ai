import { useState } from "react";
import { Download } from "lucide-react";
import { fetchReportBlob } from "../../services/api";
import { saveBlob } from "../../services/download";

type Format = "markdown" | "json";

const EXTENSION: Record<Format, string> = { markdown: "md", json: "json" };

type Message = { kind: "success" | "error"; text: string };

export default function ReportCard({ scanId }: { scanId: string }) {
  const [includeAi, setIncludeAi] = useState(false);
  const [busy, setBusy] = useState<Format | null>(null);
  const [message, setMessage] = useState<Message | null>(null);

  async function download(format: Format) {
    if (busy) return;
    setBusy(format);
    setMessage(null);
    try {
      const blob = await fetchReportBlob(scanId, format, includeAi);
      const filename = `sentinel-report-${scanId.slice(0, 8)}.${EXTENSION[format]}`;
      saveBlob(blob, filename);
      setMessage({
        kind: "success",
        text: `Download started: ${filename}${includeAi ? " (with AI content)" : ""}.`,
      });
    } catch (error) {
      setMessage({
        kind: "error",
        text: error instanceof Error ? error.message : "The report could not be downloaded.",
      });
    } finally {
      setBusy(null);
    }
  }

  return (
    <article className="card">
      <div className="panel-head">
        <div>
          <div className="panel-title">Export report</div>
          <div className="panel-sub">Download this scan&apos;s results as a file</div>
        </div>
      </div>

      <div className="card-body stack">
        <div className="report-grid">
          <div className="report-option">
            <div>
              <h3>Markdown (.md)</h3>
              <p>
                A readable report for people: summary, scanner coverage, and every finding with its
                evidence and code excerpt. Open it in any Markdown viewer.
              </p>
            </div>
            <div>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={busy !== null}
                onClick={() => void download("markdown")}
              >
                <Download aria-hidden="true" />
                {busy === "markdown" ? "Preparing..." : "Download Markdown"}
              </button>
            </div>
          </div>

          <div className="report-option">
            <div>
              <h3>JSON (.json)</h3>
              <p>
                The same data in a structured form, for scripts, dashboards, or importing into other
                tools. Scanner evidence is stored exactly as the scanners reported it.
              </p>
            </div>
            <div>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                disabled={busy !== null}
                onClick={() => void download("json")}
              >
                <Download aria-hidden="true" />
                {busy === "json" ? "Preparing..." : "Download JSON"}
              </button>
            </div>
          </div>
        </div>

        <label className="check">
          <input
            type="checkbox"
            checked={includeAi}
            onChange={(event) => setIncludeAi(event.target.checked)}
          />
          <span>
            Include AI content
            <small>
              Adds the AI explanations and suggested patches you have already generated for this
              scan. They are labeled AI-generated and untested, and nothing new is generated for the
              export. Leave this off to share scanner evidence only.
            </small>
          </span>
        </label>

        {message && (
          <p
            role={message.kind === "error" ? "alert" : "status"}
            className={`alert ${message.kind === "error" ? "alert-error" : "alert-info"}`}
          >
            {message.text}
          </p>
        )}

        <p className="fine-print" style={{ margin: 0 }}>
          Reports contain code excerpts from your repository. Treat them as sensitive and do not
          commit them or share them publicly.
        </p>
      </div>
    </article>
  );
}
