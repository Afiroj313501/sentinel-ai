import { useApi } from "../../hooks/useApi";
import { fetchHealth } from "../../services/api";

export default function BackendStatus() {
  const { state } = useApi(fetchHealth, "health");
  const online = state.status === "success";
  const label = state.status === "loading" ? "Checking backend" : online ? "Backend online" : "Backend offline";
  const dot = state.status === "loading" ? "dot-idle" : online ? "dot-ok" : "dot-bad";
  return <div className="status-card" role="status"><div className="status-row"><i className={`status-dot ${dot}`} aria-hidden="true" />{label}</div><p>{online ? "Ready to scan repositories" : "Start the API server to continue"}</p></div>;
}
