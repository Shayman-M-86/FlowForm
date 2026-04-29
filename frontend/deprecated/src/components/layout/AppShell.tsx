import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import type { AppMode } from "../../hooks/useAppMode";
import "./AppShell.css";

interface AppShellProps {
  mode: AppMode;
  onModeSwitch: (m: AppMode) => void;
}

export function AppShell({ mode, onModeSwitch }: AppShellProps) {
  return (
    <div className="app-shell">
      <Sidebar mode={mode} onModeSwitch={onModeSwitch} />
      <main className="app-shell__main">
        <Outlet />
      </main>
    </div>
  );
}
