import { useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { FileArchive, Upload } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { uploadScan } from "../services/api";
import { formatBytes } from "../services/format";

const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;

function validateFile(file: File): string | null {
  if (!file.name.toLowerCase().endsWith(".zip")) return "Please choose a .zip file.";
  if (file.size === 0) return "That file is empty.";
  if (file.size > MAX_UPLOAD_BYTES) return `That file is ${formatBytes(file.size)}. The limit is ${formatBytes(MAX_UPLOAD_BYTES)}.`;
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
    <div className="new-scan-page">
      <section className="welcome">
        <div>
          <div className="eyebrow">SECURITY WORKSPACE</div>
          <h1>New scan</h1>
          <p>Upload a repository and let Sentinel analyze it for security findings.</p>
        </div>
      </section>

      <form className="card upload-card" onSubmit={handleSubmit}>
        <div className="upload-header">
          <div className="upload-icon"><Upload aria-hidden="true" /></div>
          <div>
            <h2>Upload source code</h2>
            <p>Choose a ZIP archive containing the repository you want to scan.</p>
          </div>
        </div>
        <label className="dropzone">
          <FileArchive aria-hidden="true" />
          <strong>{file ? file.name : "Choose a ZIP file"}</strong>
          <span>{file ? `${formatBytes(file.size)} selected` : `Maximum size ${formatBytes(MAX_UPLOAD_BYTES)}`}</span>
          <input type="file" accept=".zip,application/zip" onChange={handleFileChange} disabled={scanning} />
        </label>
        <div className="scan-notes">
          <span>Files are analyzed on the server and are never executed.</span>
          <span>Dependency checks need internet access.</span>
        </div>
        {error && <p role="alert" className="scan-error">{error}</p>}
        {scanning && <p role="status" className="scan-progress">Scanning... this can take a minute or two. Please keep this page open.</p>}
        <div className="upload-actions">
          <button type="submit" disabled={!file || scanning} className="btn btn-primary">
            <Upload aria-hidden="true" />{scanning ? "Scanning..." : "Start scan"}
          </button>
        </div>
      </form>
    </div>
  );
}
