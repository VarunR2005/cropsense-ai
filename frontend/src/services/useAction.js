import { useCallback, useState } from "react";

// Wraps an async API call with loading / error / data state.
export function useAction(fn) {
  const [state, setState] = useState({ loading: false, error: null, data: null });

  const run = useCallback(
    async (...args) => {
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const data = await fn(...args);
        setState({ loading: false, error: null, data });
        return data;
      } catch (e) {
        setState({ loading: false, error: e.message, data: null });
        return undefined;
      }
    },
    [fn]
  );

  return { ...state, run };
}
