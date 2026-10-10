import { useEffect, useState } from "react";
import { fetchHealth } from "./services/api";
import type { HealthResponse } from "./types/health";

type HealthState =
  | { kind: "loading" }
  | { kind: "ok"; data: HealthResponse }
  | { kind: "error"; message: string };

export default function App() {
  const [state, setState] = useState<HealthState>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    fetchHealth(controller.signal)
      .then((data) => setState({ kind: "ok", data }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setState({
          kind: "error",
          message: error instanceof Error ? error.message : "Unknown error",
        });
      });

    return () => controller.abort();
  }, []);

  return (
    <main className="container">
      <h1>Sentinel AI</h1>
      <p className="subtitle">AI-powered code review and security analysis</p>

      <section className="card">
        <h2>Backend status</h2>
        {state.kind === "loading" && <p>Checking backend…</p>}
        {state.kind === "error" && (
          <p className="error">Backend unreachable: {state.message}</p>
        )}
        {state.kind === "ok" && (
          <ul>
            <li>Status: <strong>{state.data.status}</strong></li>
            <li>App: {state.data.app}</li>
            <li>Version: {state.data.version}</li>
            <li>Environment: {state.data.environment}</li>
          </ul>
        )}
      </section>
    </main>
  );
}