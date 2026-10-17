import { useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Upload } from "lucide-react";
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
    <div className="max-w-xl">
      <h1 className="text-2xl font-semibold">New scan</h1>
      <p className="mt-2 text-sm text-gray-600">Upload a ZIP of your source code. Files are analyzed on the server and are never executed. Maximum size: {formatBytes(MAX_UPLOAD_BYTES)}. Dependency checks need internet access.</p>
      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <input type="file" accept=".zip,application/zip" onChange={handleFileChange} disabled={scanning} className="block w-full text-sm text-gray-700 file:mr-4 file:rounded-md file:border-0 file:bg-indigo-50 file:px-4 file:py-2 file:text-sm file:font-medium file:text-indigo-700 hover:file:bg-indigo-100" />
        {file && !scanning && <p className="text-sm text-gray-600">Selected: {file.name} ({formatBytes(file.size)})</p>}
        {error && <p role="alert" className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p>}
        {scanning && <p role="status" className="text-sm text-gray-600">Scanning... this can take a minute or two. Please keep this page open.</p>}
        <button type="submit" disabled={!file || scanning} className="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"><Upload className="h-4 w-4" aria-hidden="true" />{scanning ? "Scanning..." : "Start scan"}</button>
      </form>
    </div>
  );
}
