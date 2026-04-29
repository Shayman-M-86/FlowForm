import { useState, useCallback } from "react";

export type AppMode = "manage" | "explore";

const STORAGE_KEY = "flowform_app_mode";

function readMode(): AppMode {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === "manage" || v === "explore") return v;
  } catch {
    // ignore
  }
  return "manage";
}

export function useAppMode(): [AppMode, (m: AppMode) => void] {
  const [mode, setModeState] = useState<AppMode>(readMode);

  const setMode = useCallback((m: AppMode) => {
    try {
      localStorage.setItem(STORAGE_KEY, m);
    } catch {
      // ignore
    }
    setModeState(m);
  }, []);

  return [mode, setMode];
}
