import { useCallback, useEffect, useRef, useState } from "react";

export type ApiState<T> =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; data: T };

interface Settled<T> {
  requestId: string;
  state: ApiState<T>;
}

export function useApi<T>(load: (signal: AbortSignal) => Promise<T>, key: string) {
  const [attempt, setAttempt] = useState(0);
  const [settled, setSettled] = useState<Settled<T> | null>(null);
  const loadRef = useRef(load);
  const requestId = `${key}#${attempt}`;

  useEffect(() => {
    loadRef.current = load;
  });

  useEffect(() => {
    const controller = new AbortController();
    loadRef.current(controller.signal)
      .then((data) => setSettled({ requestId, state: { status: "success", data } }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setSettled({
          requestId,
          state: {
            status: "error",
            message: error instanceof Error ? error.message : "Something went wrong.",
          },
        });
      });
    return () => controller.abort();
  }, [requestId]);

  const state: ApiState<T> =
    settled !== null && settled.requestId === requestId
      ? settled.state
      : { status: "loading" };
  const reload = useCallback(() => setAttempt((value) => value + 1), []);
  return { state, reload };
}
