import { useApi } from "../../hooks/useApi";
import { fetchHealth } from "../../services/api";

export default function BackendStatus() {
  const { state } = useApi(fetchHealth, "health");
  const online = state.status === "success";
  const label = state.status === "loading" ? "Checking backend" : online ? "Backend online" : "Backend offline";
  const dot = state.status === "loading" ? "bg-gray-400" : online ? "bg-green-500" : "bg-red-500";
  return <span className="flex items-center gap-1.5 text-xs text-gray-500"><span className={`h-2 w-2 rounded-full ${dot}`} aria-hidden="true" />{label}</span>;
}
