import { useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Link2, Upload } from "lucide-react";
import { scanGithub, uploadScan } from "../services/api";
import { formatBytes } from "../services/format";
import { validateRepoUrl } from "../services/github";
import type { ScanResult } from "../types/finding";

const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;
type Mode = "upload" | "github";

function validateFile(file: File): string | null {
  if (!file.name.toLowerCase().endsWith(".zip")) return "Please choose a .zip file.";
  if (file.size === 0) return "That file is empty.";
  if (file.size > MAX_UPLOAD_BYTES) {
    return `That file is ${formatBytes(file.size)}. The limit is ${formatBytes(MAX_UPLOAD_BYTES)}.`;
  }
  return null;
}

export default function NewScan() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);

  function switchMode(next: Mode) {
    if (scanning || next === mode) return;
    setMode(next);
    setError(null);
  }

  async function run(action: () => Promise<ScanResult>) {
    setScanning(true);
    setError(null);
    try {
      const result = await action();
      navigate(`/scans/${result.metadata.scan_id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The scan could not be completed.");
      setScanning(false);
    }
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    const problem = selected ? validateFile(selected) : null;
    setError(problem);
    setFile(selected && !problem ? selected : null);
  }

  function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || scanning) return;
    void run(() => uploadScan(file));
  }

  function handleGithub(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (scanning) return;
    const problem = validateRepoUrl(url);
    if (problem) {
      setError(problem);
      return;
    }
    void run(() => scanGithub(url.trim()));
  }

  return (
    <div>
      <section className="welcome">
        <div>
          <div className="eyebrow">NEW SCAN</div>
          <h1>Scan a repository</h1>
          <p>
            Upload a ZIP or scan a public GitHub repository. Files are analyzed on the server and
            never executed. Dependency checks need internet access.
          </p>
        </div>
      </section>

      <article className="card" style={{ maxWidth: 640 }}>
        <div className="tabs" role="group" aria-label="Scan source">
          <button
            type="button"
            className={`tab${mode === "upload" ? " active" : ""}`}
            aria-pressed={mode === "upload"}
            disabled={scanning}
            onClick={() => switchMode("upload")}
          >
            Upload ZIP
          </button>
          <button
            type="button"
            className={`tab${mode === "github" ? " active" : ""}`}
            aria-pressed={mode === "github"}
            disabled={scanning}
            onClick={() => switchMode("github")}
          >
            GitHub URL
          </button>
        </div>

        <div className="pad">
          {mode === "upload" ? (
            <form onSubmit={handleUpload} className="stack">
              <input
                type="file"
                accept=".zip,application/zip"
                onChange={handleFileChange}
                disabled={scanning}
                className="file-input"
                aria-label="Repository ZIP file"
              />
              <p className="fine-print" style={{ margin: 0 }}>
                Maximum size: {formatBytes(MAX_UPLOAD_BYTES)}.
              </p>
              {file && !scanning && (
                <p className="small muted" style={{ margin: 0 }}>
                  Selected: {file.name} ({formatBytes(file.size)})
                </p>
              )}
              {error && <p role="alert" className="alert alert-error">{error}</p>}
              {scanning && (
                <p role="status" className="alert alert-info">
                  Scanning... this can take a minute or two. Please keep this page open.
                </p>
              )}
              <div>
                <button type="submit" className="btn btn-primary" disabled={!file || scanning}>
                  <Upload aria-hidden="true" />
                  {scanning ? "Scanning..." : "Start scan"}
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleGithub} className="stack" noValidate>
              <div>
                <label htmlFor="repo-url" className="label">
                  Repository URL
                </label>
                <div className="input-wrap">
                  <Link2 aria-hidden="true" />
                  <input
                    id="repo-url"
                    type="text"
                    inputMode="url"
                    autoComplete="off"
                    spellCheck={false}
                    maxLength={300}
                    className="input"
                    placeholder="https://github.com/owner/repo"
                    value={url}
                    disabled={scanning}
                    onChange={(event) => {
                      setUrl(event.target.value);
                      setError(null);
                    }}
                  />
                </div>
                <p className="fine-print">
                  To scan a branch, use https://github.com/owner/repo/tree/branch-name
                </p>
              </div>
              <p className="alert alert-info">
                <span>
                  <strong>Public repositories only.</strong> Sentinel downloads GitHub&apos;s ZIP of
                  the repository over HTTPS. It never runs git or your code and never sends
                  credentials, so private repositories cannot be scanned. Repositories over{" "}
                  {formatBytes(MAX_UPLOAD_BYTES)} are refused.
                </span>
              </p>
              {error && <p role="alert" className="alert alert-error">{error}</p>}
              {scanning && (
                <p role="status" className="alert alert-info">
                  Downloading and scanning... this can take a minute or two. Please keep this page
                  open.
                </p>
              )}
              <div>
                <button type="submit" className="btn btn-primary" disabled={!url.trim() || scanning}>
                  <Link2 aria-hidden="true" />
                  {scanning ? "Scanning..." : "Scan repository"}
                </button>
              </div>
            </form>
          )}
        </div>
      </article>
    </div>
  );
}
