import { useCallback, useState } from "react";
import { useParams } from "react-router-dom";
import type { CreateSurveyRequest, SurveyVisibility } from "../api/types";
import { SurveyCard } from "../components/survey/SurveyCard";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";
import { Select } from "../components/ui/Select";
import { Spinner } from "../components/ui/Spinner";
import { Toggle } from "../components/ui/Toggle";
import { useFetch } from "../hooks/useFetch";
import "../App.css";
import "./SurveysPage.css";
import { useApi } from "../api/useApi";


const VISIBILITY_OPTIONS = [
  { value: "private", label: "Private" },
  { value: "link_only", label: "Link only" },
  { value: "public", label: "Public" },
];

export function SurveysPage() {
  const { listSurveys, createSurvey } = useApi();
  const { projectId } = useParams<{ projectId: string }>();
  const id = Number(projectId);

  const fetcher = useCallback(() => listSurveys(id), [id]);
  const { data: surveys, loading, error, refetch } = useFetch(fetcher, [id]);

  const [showCreate, setShowCreate] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState<CreateSurveyRequest>({
    title: "",
    visibility: "private",
    allow_public_responses: false,
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
      setForm({ title: "", visibility: "private", allow_public_responses: false, public_slug: null });
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Failed to create survey.");
    } finally {
      setSaving(false);
    }
  }

  const showSlug = form.visibility === "public";
  const showPublicResponses = form.visibility === "link_only" || form.visibility === "public";

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">
          Surveys <Badge variant="muted">{`Project ${String(id)}`}</Badge>
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
              <SurveyCard key={s.id} survey={s} projectId={id} />
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
          onChange={(e) => updateForm("visibility", e.target.value as SurveyVisibility)}
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
        {showPublicResponses && (
          <Toggle
            label="Allow public responses"
            checked={form.allow_public_responses ?? false}
            onChange={(v) => updateForm("allow_public_responses", v)}
          />
        )}
      </Modal>
    </div>
  );
}
