import type { AppMode } from "../../hooks/useAppMode";
import "./ModeToggle.css";

interface ModeToggleProps {
  mode: AppMode;
  onSwitch: (m: AppMode) => void;
}

export function ModeToggle({ mode, onSwitch }: ModeToggleProps) {
  return (
    <div className="mode-toggle">
      <button
        className={`mode-toggle__btn ${mode === "manage" ? "mode-toggle__btn--active" : ""}`}
        onClick={() => onSwitch("manage")}
        aria-pressed={mode === "manage"}
      >
        Manage
      </button>
      <button
        className={`mode-toggle__btn ${mode === "explore" ? "mode-toggle__btn--active" : ""}`}
        onClick={() => onSwitch("explore")}
        aria-pressed={mode === "explore"}
      >
        Explore
      </button>
    </div>
  );
}
