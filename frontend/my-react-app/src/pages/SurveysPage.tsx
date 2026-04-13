import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { CreateSurveyRequest, SurveyVisibility } from "../api/types";
import { SurveyCard } from "../components/survey/SurveyCard";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";
import { Select } from "../components/ui/Select";
import { Spinner } from "../components/ui/Spinner";
import { useFetch } from "../hooks/useFetch";
import "../App.css";
import "./SurveysPage.css";
import { useApi } from "../api/useApi";
import { projectSurveysPath } from "../components/layout/projectSelection";
import { useProjectContext } from "../hooks/useProjectContext";


const VISIBILITY_OPTIONS = [
  { value: "private", label: "Private" },
  { value: "link_only", label: "Link only" },
  { value: "public", label: "Public" },
];

export function SurveysPage() {
  const { listSurveys, createSurvey } = useApi();
  const navigate = useNavigate();
  const { projectRef: routeProjectRef } = useParams<{ projectRef: string }>();
  const { currentProject, projectId, projectRef, loading: projectLoading, error: projectError } =
    useProjectContext(routeProjectRef);
  const id = projectId ?? 0;

  useEffect(() => {
    if (
      currentProject &&
      routeProjectRef &&
      routeProjectRef !== currentProject.slug &&
      String(currentProject.id) === routeProjectRef
    ) {
      navigate(projectSurveysPath(currentProject), { replace: true });
    }
  }, [currentProject, navigate, routeProjectRef]);

  const fetcher = useCallback(
    () => (projectId ? listSurveys(projectId) : Promise.resolve([])),
    [listSurveys, projectId],
  );
  const { data: surveys, loading, error, refetch } = useFetch(projectId ? fetcher : null, [projectId]);

  const [showCreate, setShowCreate] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState<CreateSurveyRequest>({
    title: "",
    visibility: "private",
    public_slug: null,
  });

  function updateForm<K extends keyof CreateSurveyRequest>(
    key: K,
    value: CreateSurveyRequest[K],
  ) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleCreate() {
    if (!form.title.trim()) return;
    setSaving(true);
    setCreateError(null);
    try {
      await createSurvey(id, form);
      refetch();
      setShowCreate(false);
      setForm({ title: "", visibility: "private", public_slug: null });
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Failed to create survey.");
    } finally {
      setSaving(false);
    }
  }

  const showSlug = form.visibility === "public";
  if (projectLoading) return <div className="page"><Spinner /></div>;
  if (projectError) return <div className="page"><div className="error-banner">{projectError}</div></div>;
  if (!currentProject || !projectRef) return <div className="page"><div className="error-banner">Project not found.</div></div>;

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">
          Surveys <Badge variant="muted">{currentProject.slug}</Badge>
        </h1>
        <Button variant="primary" onClick={() => setShowCreate(true)}>
          + New Survey
        </Button>
      </div>

      {loading && <Spinner />}
      {error && <div className="error-banner">{error}</div>}

      {surveys && (
        surveys.length === 0 ? (
          <div className="empty-state">No surveys yet. Create your first quiz.</div>
        ) : (
          <div className="surveys-grid">
            {surveys.map((s) => (
              <SurveyCard key={s.id} survey={s} projectRef={projectRef} />
            ))}
          </div>
        )
      )}

      <Modal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title="New Survey"
        footer={
          <>
            <Button variant="ghost" onClick={() => setShowCreate(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={handleCreate} disabled={saving || !form.title.trim()}>
              {saving ? "Creating…" : "Create"}
            </Button>
          </>
        }
      >
        {createError && <div className="error-banner">{createError}</div>}
        <Input
          label="Title"
          value={form.title}
          onChange={(e) => updateForm("title", e.target.value)}
          placeholder="My Quiz"
          autoFocus
        />
        <Select
          label="Visibility"
          options={VISIBILITY_OPTIONS}
          value={form.visibility}
          onChange={(e) => {
            const visibility = e.target.value as SurveyVisibility;
            setForm((prev) => ({
              ...prev,
              visibility,
              public_slug: visibility === "public" ? prev.public_slug : null,
            }));
          }}
        />
        {showSlug && (
          <Input
            label="Public slug"
            value={form.public_slug ?? ""}
            onChange={(e) => updateForm("public_slug", e.target.value || null)}
            placeholder="my-quiz"
            hint="Used in the public URL: /quiz/{slug}"
          />
        )}
      </Modal>
    </div>
  );
}
