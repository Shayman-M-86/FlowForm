import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import type { SurveyVersionOut, VersionStatus } from "../../api/types";
import "./VersionBar.css";

interface VersionBarProps {
  versions: SurveyVersionOut[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  onNewDraft: () => void;
  onPublish: (versionId: number) => void;
  onArchive: (versionId: number) => void;
  busy: boolean;
}

const STATUS_BADGE: Record<VersionStatus, "muted" | "success" | "warning"> = {
  draft: "warning",
  published: "success",
  archived: "muted",
};

export function VersionBar({
  versions,
  selectedId,
  onSelect,
  onNewDraft,
  onPublish,
  onArchive,
  busy,
}: VersionBarProps) {
  const selected = versions.find((v) => v.id === selectedId);

  return (
    <div className="version-bar">
      <div className="version-bar__left">
        <span className="version-bar__label">Version</span>
        <select
          className="version-bar__select"
          value={selectedId ?? ""}
          onChange={(e) => onSelect(Number(e.target.value))}
          disabled={versions.length === 0}
        >
          {versions.length === 0 && <option value="">No versions</option>}
          {versions.map((v) => (
            <option key={v.id} value={v.id}>
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
            onClick={() => onPublish(selected.id)}
            disabled={busy}
          >
            Publish
          </Button>
        )}
        {selected?.status === "published" && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => onArchive(selected.id)}
            disabled={busy}
          >
            Archive
          </Button>
        )}
      </div>
    </div>
  );
}
