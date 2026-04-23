import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { SurveyOut, SurveyVisibility, UpdateSurveyRequest } from "../api/types";
import { PublicLinkList } from "../components/survey/PublicLinkList";
import { QuestionList } from "../components/survey/QuestionList";
import { RuleList } from "../components/survey/RuleList";
import { ScoringRuleList } from "../components/survey/ScoringRuleList";
import { VersionBar } from "../components/survey/VersionBar";
import { Button, Input, Modal, Select, Spinner, Badge } from "../index.optimized";
import { useFetch } from "../hooks/useFetch";
import "../App.css";
import "./SurveyEditorPage.css";
import { useApi } from "../api/useApi";
import { projectSurveyPath } from "../components/layout/projectSelection";
import { useProjectContext } from "../hooks/useProjectContext";

type EditorTab = "questions" | "rules" | "scoring" | "links";
type MountedPanel = {
  key: string;
  tab: EditorTab;
  versionNumber: number | null;
};

const TABS: { id: EditorTab; label: string }[] = [
  { id: "questions", label: "Questions" },
  { id: "rules", label: "Rules" },
  { id: "scoring", label: "Scoring" },
  { id: "links", label: "Links" },
];

export function SurveyEditorPage() {
  const navigate = useNavigate();
  const { projectRef: routeProjectRef, surveyId } = useParams<{
    projectRef: string;
    surveyId: string;
  }>();

  const { currentProject, projectId, projectRef, loading: projectLoading, error: projectError } =
    useProjectContext(routeProjectRef);
  const pid = projectId ?? 0;
  const sid = Number(surveyId);

  const {
    getSurvey,
    listVersions,
    createVersion,
    copyVersionToDraft,
    publishVersion,
    archiveVersion,
    updateSurvey,
  } = useApi();

  const surveyFetcher = useCallback(
    () => (projectRef ? getSurvey(projectRef, sid) : Promise.reject(new Error("Project not found."))),
    [getSurvey, projectRef, sid],
  );
  const { data: survey, loading: surveyLoading, error: surveyError, refetch: refetchSurvey } =
    useFetch(projectRef ? surveyFetcher : null, [projectRef, sid]);

  const versionsFetcher = useCallback(
    () => (projectRef ? listVersions(projectRef, sid) : Promise.resolve([])),
    [listVersions, projectRef, sid],
  );
  const { data: versions, loading: versionsLoading, refetch: refetchVersions } =
    useFetch(projectRef ? versionsFetcher : null, [projectRef, sid]);

  useEffect(() => {
    if (
      currentProject &&
      routeProjectRef &&
      routeProjectRef !== currentProject.slug &&
      String(currentProject.id) === routeProjectRef
    ) {
      navigate(projectSurveyPath(currentProject, sid), { replace: true });
    }
  }, [currentProject, navigate, routeProjectRef, sid]);

  const [selectedVersionNumber, setSelectedVersionNumber] = useState<number | null>(null);
  const [tab, setTab] = useState<EditorTab>("questions");
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
  const resolvedVersionNumber =
    selectedVersionNumber ??
    (versions && versions.length > 0 ? versions[versions.length - 1].version_number : null);

  const selectedVersion =
    versions?.find((version) => version.version_number === resolvedVersionNumber) ?? null;
  const isReadOnly = selectedVersion?.status !== "draft";
  const activePanel: MountedPanel | null =
    tab === "links"
      ? { key: `${pid}:${sid}:links`, tab: "links", versionNumber: null }
      : resolvedVersionNumber === null
        ? null
        : {
            key: `${pid}:${sid}:${tab}:${resolvedVersionNumber}`,
            tab,
            versionNumber: resolvedVersionNumber,
          };

  function renderPanel(panel: MountedPanel) {
    const panelIsReadOnly =
      panel.versionNumber === null
        ? isReadOnly
        : (versions?.find((version) => version.version_number === panel.versionNumber)?.status ??
            "draft") !== "draft";

    switch (panel.tab) {
      case "questions":
        if (panel.versionNumber === null) return null;
        return (
          <QuestionList
            projectId={pid}
            surveyId={sid}
            versionNumber={panel.versionNumber}
            readOnly={panelIsReadOnly}
          />
        );
      case "rules":
        if (panel.versionNumber === null) return null;
        return (
          <RuleList
            projectId={pid}
            surveyId={sid}
            versionNumber={panel.versionNumber}
            readOnly={panelIsReadOnly}
          />
        );
      case "scoring":
        if (panel.versionNumber === null) return null;
        return (
          <ScoringRuleList
            projectId={pid}
            surveyId={sid}
            versionNumber={panel.versionNumber}
            readOnly={panelIsReadOnly}
          />
        );
      case "links":
        return (
          <PublicLinkList
            projectId={pid}
            surveyId={sid}
            surveyVisibility={survey?.visibility ?? "private"}
          />
        );
    }
  }

  async function handleNewDraft() {
    setVersionBusy(true);
    try {
      const v = await createVersion(projectRef!, sid);
      refetchVersions();
      setSelectedVersionNumber(v.version_number);
    } finally {
      setVersionBusy(false);
    }
  }

  async function handlePublish(versionNumber: number) {
    setVersionBusy(true);
    try {
      await publishVersion(projectRef!, sid, versionNumber);
      refetchVersions();
      refetchSurvey();
    } finally {
      setVersionBusy(false);
    }
  }

  async function handleCopyToDraft(versionNumber: number) {
    setVersionBusy(true);
    try {
      const version = await copyVersionToDraft(projectRef!, sid, versionNumber);
      refetchVersions();
      setSelectedVersionNumber(version.version_number);
      setTab("questions");
    } finally {
      setVersionBusy(false);
    }
  }

  async function handleArchive(versionNumber: number) {
    setVersionBusy(true);
    try {
      await archiveVersion(projectRef!, sid, versionNumber);
      refetchVersions();
      refetchSurvey();
    } finally {
      setVersionBusy(false);
    }
  }

  async function handleTitleSave() {
    if (!titleValue.trim() || titleValue === survey?.title) {
      setEditingTitle(false);
      return;
    }
    await updateSurvey(projectRef!, sid, { title: titleValue.trim() });
    refetchSurvey();
    setEditingTitle(false);
  }

  function openSettings(s: SurveyOut) {
    setSettingsForm({
      title: s.title,
      visibility: s.visibility,
      public_slug: s.public_slug,
    });
    setSettingsError(null);
    setSettingsOpen(true);
  }

  async function handleSettingsSave() {
    setSettingsSaving(true);
    setSettingsError(null);
    try {
      await updateSurvey(projectRef!, sid, settingsForm);
      refetchSurvey();
      setSettingsOpen(false);
    } catch (err) {
      setSettingsError(err instanceof Error ? err.message : "Failed to save settings.");
    } finally {
      setSettingsSaving(false);
    }
  }

  if (projectLoading || surveyLoading || versionsLoading) {
    return (
      <div className="page page--loading">
        <Spinner /> Loading…
      </div>
    );
  }

  if (projectError || surveyError || !currentProject || !projectRef) {
    return <div className="page"><div className="error-banner">{projectError ?? surveyError ?? "Project not found."}</div></div>;
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
          {survey && <Badge variant="muted">{currentProject.slug}</Badge>}
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
          selectedVersionNumber={resolvedVersionNumber}
          onSelect={setSelectedVersionNumber}
          onNewDraft={handleNewDraft}
          onCopyToDraft={handleCopyToDraft}
          onPublish={handlePublish}
          onArchive={handleArchive}
          busy={versionBusy}
        />
      )}

      {resolvedVersionNumber === null ? (
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
            {activePanel && (
              <div key={activePanel.key} className="tab-panel">
                {renderPanel(activePanel)}
              </div>
            )}
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
            onChange={(e) => {
              const visibility = e.target.value as SurveyVisibility;
              setSettingsForm((p) => ({
                ...p,
                visibility,
                public_slug: visibility === "public" ? p.public_slug : null,
              }));
            }}
          />
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
