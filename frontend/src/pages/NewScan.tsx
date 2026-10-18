import { useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Upload } from "lucide-react";
import { uploadScan } from "../services/api";
import { formatBytes } from "../services/format";

const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;

// Quick client-side checks to save a pointless upload. The server stays the authority.
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
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    const problem = selected ? validateFile(selected) : null;
    setError(problem);
    setFile(selected && !problem ? selected : null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || scanning) return;
    setScanning(true);
    setError(null);
    try {
      const result = await uploadScan(file);
      navigate(`/scans/${result.metadata.scan_id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The scan could not be completed.");
      setScanning(false);
    }
  }

  return (
    <div>
      <section className="welcome">
        <div>
          <div className="eyebrow">NEW SCAN</div>
          <h1>Scan a repository</h1>
          <p>
            Upload a ZIP of your source code. Files are analyzed on the server and never executed.
            Maximum size: {formatBytes(MAX_UPLOAD_BYTES)}. Dependency checks need internet access.
          </p>
        </div>
      </section>

      <article className="card pad" style={{ maxWidth: 640 }}>
        <form onSubmit={handleSubmit} className="stack">
          <input
            type="file"
            accept=".zip,application/zip"
            onChange={handleFileChange}
            disabled={scanning}
            className="file-input"
            aria-label="Repository ZIP file"
          />
          {file && !scanning && (
            <p className="small muted" style={{ margin: 0 }}>
              Selected: {file.name} ({formatBytes(file.size)})
            </p>
          )}
          {error && (
            <p role="alert" className="alert alert-error">
              {error}
            </p>
          )}
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
      </article>
    </div>
  );
}
