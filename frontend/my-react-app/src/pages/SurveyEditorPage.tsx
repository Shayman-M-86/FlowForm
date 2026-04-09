import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import type { SurveyOut, SurveyVisibility, UpdateSurveyRequest } from "../api/types";
import { PublicLinkList } from "../components/survey/PublicLinkList";
import { QuestionList } from "../components/survey/QuestionList";
import { RuleList } from "../components/survey/RuleList";
import { ScoringRuleList } from "../components/survey/ScoringRuleList";
import { VersionBar } from "../components/survey/VersionBar";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";
import { Select } from "../components/ui/Select";
import { Spinner } from "../components/ui/Spinner";
import { Toggle } from "../components/ui/Toggle";
import { useFetch } from "../hooks/useFetch";
import "../App.css";
import "./SurveyEditorPage.css";
import { useApi } from "../api/useApi";

type EditorTab = "questions" | "rules" | "scoring" | "links";
type MountedPanel = {
  key: string;
  tab: EditorTab;
  versionId: number | null;
};

const TABS: { id: EditorTab; label: string }[] = [
  { id: "questions", label: "Questions" },
  { id: "rules", label: "Rules" },
  { id: "scoring", label: "Scoring" },
  { id: "links", label: "Links" },
];

export function SurveyEditorPage() {
  const { projectId, surveyId } = useParams<{
    projectId: string;
    surveyId: string;
  }>();

  const pid = Number(projectId);
  const sid = Number(surveyId);

  const {
    getSurvey,
    listVersions,
    createVersion,
    publishVersion,
    archiveVersion,
    updateSurvey,
  } = useApi();

  const surveyFetcher = useCallback(() => getSurvey(pid, sid), [getSurvey, pid, sid]);
  const { data: survey, loading: surveyLoading, error: surveyError, refetch: refetchSurvey } =
    useFetch(surveyFetcher);

  const versionsFetcher = useCallback(
    () => listVersions(pid, sid),
    [listVersions, pid, sid],
  );
  const { data: versions, loading: versionsLoading, refetch: refetchVersions } =
    useFetch(versionsFetcher);

  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null);
  const [tab, setTab] = useState<EditorTab>("questions");
  const [mountedPanels, setMountedPanels] = useState<MountedPanel[]>([]);
  const [versionBusy, setVersionBusy] = useState(false);

  // Inline title edit
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleValue, setTitleValue] = useState("");

  // Survey settings modal
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsForm, setSettingsForm] = useState<UpdateSurveyRequest>({});
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsError, setSettingsError] = useState<string | null>(null);

  // Resolve selected version (prefer the one selected; fall back to latest)
  const resolvedVersionId =
    selectedVersionId ??
    (versions && versions.length > 0 ? versions[versions.length - 1].id : null);

  const selectedVersion = versions?.find((v) => v.id === resolvedVersionId) ?? null;
  const isReadOnly = selectedVersion?.status !== "draft";
  const activePanel: MountedPanel | null =
    tab === "links"
      ? { key: `${pid}:${sid}:links`, tab: "links", versionId: null }
      : resolvedVersionId === null
        ? null
        : {
            key: `${pid}:${sid}:${tab}:${resolvedVersionId}`,
            tab,
            versionId: resolvedVersionId,
          };

  useEffect(() => {
    setMountedPanels([]);
  }, [pid, sid]);

  useEffect(() => {
    if (!activePanel) return;
    setMountedPanels((current) =>
      current.some((panel) => panel.key === activePanel.key)
        ? current
        : [...current, activePanel],
    );
  }, [activePanel]);

  const renderedPanels =
    activePanel && !mountedPanels.some((panel) => panel.key === activePanel.key)
      ? [...mountedPanels, activePanel]
      : mountedPanels;

  function renderPanel(panel: MountedPanel) {
    const panelIsReadOnly =
      panel.versionId === null
        ? isReadOnly
        : (versions?.find((version) => version.id === panel.versionId)?.status ?? "draft") !== "draft";

    switch (panel.tab) {
      case "questions":
        if (panel.versionId === null) return null;
        return (
          <QuestionList
            projectId={pid}
            surveyId={sid}
            versionId={panel.versionId}
            readOnly={panelIsReadOnly}
          />
        );
      case "rules":
        if (panel.versionId === null) return null;
        return (
          <RuleList
            projectId={pid}
            surveyId={sid}
            versionId={panel.versionId}
            readOnly={panelIsReadOnly}
          />
        );
      case "scoring":
        if (panel.versionId === null) return null;
        return (
          <ScoringRuleList
            projectId={pid}
            surveyId={sid}
            versionId={panel.versionId}
            readOnly={panelIsReadOnly}
          />
        );
      case "links":
        return <PublicLinkList projectId={pid} surveyId={sid} />;
    }
  }

  async function handleNewDraft() {
    setVersionBusy(true);
    try {
      const v = await createVersion(pid, sid);
      refetchVersions();
      setSelectedVersionId(v.id);
    } finally {
      setVersionBusy(false);
    }
  }

  async function handlePublish(versionId: number) {
    setVersionBusy(true);
    try {
      await publishVersion(pid, sid, versionId);
      refetchVersions();
      refetchSurvey();
    } finally {
      setVersionBusy(false);
    }
  }

  async function handleArchive(versionId: number) {
    setVersionBusy(true);
    try {
      await archiveVersion(pid, sid, versionId);
      refetchVersions();
    } finally {
      setVersionBusy(false);
    }
  }

  async function handleTitleSave() {
    if (!titleValue.trim() || titleValue === survey?.title) {
      setEditingTitle(false);
      return;
    }
    await updateSurvey(pid, sid, { title: titleValue.trim() });
    refetchSurvey();
    setEditingTitle(false);
  }

  function openSettings(s: SurveyOut) {
    setSettingsForm({
      title: s.title,
      visibility: s.visibility,
      allow_public_responses: s.allow_public_responses,
      public_slug: s.public_slug,
    });
    setSettingsError(null);
    setSettingsOpen(true);
  }

  async function handleSettingsSave() {
    setSettingsSaving(true);
    setSettingsError(null);
    try {
      await updateSurvey(pid, sid, settingsForm);
      refetchSurvey();
      setSettingsOpen(false);
    } catch (err) {
      setSettingsError(err instanceof Error ? err.message : "Failed to save settings.");
    } finally {
      setSettingsSaving(false);
    }
  }

  if (surveyLoading || versionsLoading) {
    return (
      <div className="page page--loading">
        <Spinner /> Loading…
      </div>
    );
  }

  if (surveyError) {
    return <div className="page"><div className="error-banner">{surveyError}</div></div>;
  }

  return (
    <div className="page">
      {/* Survey header */}
      <div className="editor-header">
        <div className="editor-header__title">
          {editingTitle ? (
            <input
              className="editor-title-input"
              value={titleValue}
              onChange={(e) => setTitleValue(e.target.value)}
              onBlur={handleTitleSave}
              onKeyDown={(e) => { if (e.key === "Enter") handleTitleSave(); if (e.key === "Escape") setEditingTitle(false); }}
              autoFocus
            />
          ) : (
            <h1
              className="editor-title"
              onClick={() => {
                setTitleValue(survey?.title ?? "");
                setEditingTitle(true);
              }}
              title="Click to edit title"
            >
              {survey?.title ?? "—"}
            </h1>
          )}
          {survey && <Badge variant="muted">{survey.visibility.replace("_", " ")}</Badge>}
        </div>
        <div className="editor-header__actions">
          {survey && (
            <Button size="sm" variant="ghost" onClick={() => openSettings(survey)}>
              ⚙ Settings
            </Button>
          )}
        </div>
      </div>

      {/* Version bar */}
      {versions && (
        <VersionBar
          versions={versions}
          selectedId={resolvedVersionId}
          onSelect={setSelectedVersionId}
          onNewDraft={handleNewDraft}
          onPublish={handlePublish}
          onArchive={handleArchive}
          busy={versionBusy}
        />
      )}

      {resolvedVersionId === null ? (
        <div className="empty-state">
          No versions yet. Create a draft to start adding questions.
        </div>
      ) : (
        <>
          {isReadOnly && (
            <div className="editor-readonly-banner">
              This version is {selectedVersion?.status} — editing is disabled.
            </div>
          )}

          {/* Tabs */}
          <div className="tabs">
            {TABS.map((t) => (
              <button
                key={t.id}
                className={`tab ${tab === t.id ? "tab--active" : ""}`}
                onClick={() => setTab(t.id)}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="tab-panels">
            {renderedPanels.map((panel) => {
              const isActivePanel = panel.key === activePanel?.key;

              return (
                <div
                  key={panel.key}
                  className={`tab-panel ${isActivePanel ? "" : "tab-panel--hidden"}`}
                  hidden={!isActivePanel}
                >
                  {renderPanel(panel)}
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* Survey settings modal */}
      {survey && (
        <Modal
          open={settingsOpen}
          onClose={() => setSettingsOpen(false)}
          title="Survey Settings"
          footer={
            <>
              <Button variant="ghost" onClick={() => setSettingsOpen(false)}>Cancel</Button>
              <Button variant="primary" onClick={handleSettingsSave} disabled={settingsSaving}>
                {settingsSaving ? "Saving…" : "Save"}
              </Button>
            </>
          }
        >
          {settingsError && <div className="error-banner">{settingsError}</div>}
          <Input
            label="Title"
            value={settingsForm.title ?? ""}
            onChange={(e) =>
              setSettingsForm((p) => ({ ...p, title: e.target.value }))
            }
          />
          <Select
            label="Visibility"
            options={[
              { value: "private", label: "Private" },
              { value: "link_only", label: "Link only" },
              { value: "public", label: "Public" },
            ]}
            value={settingsForm.visibility ?? "private"}
            onChange={(e) =>
              setSettingsForm((p) => ({ ...p, visibility: e.target.value as SurveyVisibility }))
            }
          />
          {(settingsForm.visibility === "link_only" ||
            settingsForm.visibility === "public") && (
            <Toggle
              label="Allow public responses"
              checked={settingsForm.allow_public_responses ?? false}
              onChange={(v) =>
                setSettingsForm((p) => ({ ...p, allow_public_responses: v }))
              }
            />
          )}
          {settingsForm.visibility === "public" && (
            <Input
              label="Public slug"
              value={settingsForm.public_slug ?? ""}
              onChange={(e) =>
                setSettingsForm((p) => ({ ...p, public_slug: e.target.value || null }))
              }
              placeholder="my-quiz"
            />
          )}
        </Modal>
      )}
    </div>
  );
}
