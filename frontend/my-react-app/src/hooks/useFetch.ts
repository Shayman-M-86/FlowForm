import { useCallback, useEffect, useRef, useState, type DependencyList } from "react";
import { ApiRequestError } from "../api/client";

export interface FetchState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useFetch<T>(
  fetcher: (() => Promise<T>) | null,
  deps?: DependencyList,
): FetchState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const counterRef = useRef(0);
  const fetcherRef = useRef(fetcher);

  useEffect(() => {
    fetcherRef.current = fetcher;
  }, [fetcher]);

  const run = useCallback(() => {
    const currentFetcher = fetcherRef.current;
    if (!currentFetcher) return;
    const id = ++counterRef.current;
    setLoading(true);
    setError(null);
    currentFetcher()
      .then((result) => {
        if (id === counterRef.current) {
          setData(result);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (id === counterRef.current) {
          if (err instanceof ApiRequestError) {
            setError(err.error.message);
          } else if (err instanceof Error) {
            setError(err.message);
          } else {
            setError("An unexpected error occurred.");
          }
          setLoading(false);
        }
      });
  }, []);

  useEffect(() => {
    run();
  }, [run, ...(deps ?? [fetcher])]);

  return { data, loading, error, refetch: run };
}
