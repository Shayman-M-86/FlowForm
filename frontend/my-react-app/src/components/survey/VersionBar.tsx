import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import type { SurveyVersionOut, VersionStatus } from "../../api/types";
import "./VersionBar.css";

interface VersionBarProps {
  versions: SurveyVersionOut[];
  selectedVersionNumber: number | null;
  onSelect: (versionNumber: number) => void;
  onNewDraft: () => void;
  onPublish: (versionNumber: number) => void;
  onArchive: (versionNumber: number) => void;
  busy: boolean;
}

const STATUS_BADGE: Record<VersionStatus, "muted" | "success" | "warning"> = {
  draft: "warning",
  published: "success",
  archived: "muted",
};

export function VersionBar({
  versions,
  selectedVersionNumber,
  onSelect,
  onNewDraft,
  onPublish,
  onArchive,
  busy,
}: VersionBarProps) {
  const selected = versions.find((v) => v.version_number === selectedVersionNumber);

  return (
    <div className="version-bar">
      <div className="version-bar__left">
        <span className="version-bar__label">Version</span>
        <select
          className="version-bar__select"
          value={selectedVersionNumber ?? ""}
          onChange={(e) => onSelect(Number(e.target.value))}
          disabled={versions.length === 0}
        >
          {versions.length === 0 && <option value="">No versions</option>}
          {versions.map((v) => (
            <option key={v.version_number} value={v.version_number}>
              v{v.version_number} — {v.status}
            </option>
          ))}
        </select>
        {selected && <Badge variant={STATUS_BADGE[selected.status]}>{selected.status}</Badge>}
      </div>

      <div className="version-bar__actions">
        <Button size="sm" variant="secondary" onClick={onNewDraft} disabled={busy}>
          New Draft
        </Button>
        {selected?.status === "draft" && (
          <Button
            size="sm"
            variant="primary"
            onClick={() => onPublish(selected.version_number)}
            disabled={busy}
          >
            Publish
          </Button>
        )}
        {selected?.status === "published" && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => onArchive(selected.version_number)}
            disabled={busy}
          >
            Archive
          </Button>
        )}
      </div>
    </div>
  );
}
