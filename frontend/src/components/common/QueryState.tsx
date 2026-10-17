import type { ReactNode } from "react";
import type { ApiState } from "../../hooks/useApi";

interface QueryStateProps<T> {
  state: ApiState<T>;
  onRetry: () => void;
  children: (data: T) => ReactNode;
}

export default function QueryState<T>({ state, onRetry, children }: QueryStateProps<T>) {
  if (state.status === "loading") return <p className="text-sm text-gray-500">Loading...</p>;
  if (state.status === "error") {
    return (
      <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
        <p>{state.message}</p>
        <button type="button" onClick={onRetry} className="mt-2 font-medium underline">Try again</button>
      </div>
    );
  }
  return <>{children(state.data)}</>;
}
