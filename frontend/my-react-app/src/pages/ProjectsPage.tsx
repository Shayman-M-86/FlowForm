import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { CreateProjectRequest } from "../api/types";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";
import { Spinner } from "../components/ui/Spinner";
import { useFetch } from "../hooks/useFetch";
import { useApi } from "../api/useApi";
import "../App.css";

function nameToSlug(name: string): string {
  return name
    .toLowerCase()
    .replace(/\s+/g, "-")       // spaces → hyphens
    .replace(/[^a-z0-9-]/g, "") // strip anything else
    .replace(/-+/g, "-")        // collapse consecutive hyphens
    .replace(/^-+|-+$/g, "");   // trim leading/trailing hyphens
}

function validateSlug(slug: string): string | null {
  if (!slug) return null; // no input yet — no error
  if (!/^[a-z0-9-]+$/.test(slug)) return "Slug may only contain lowercase letters, numbers, and hyphens.";
  if (/^-|-$/.test(slug)) return "Slug cannot start or end with a hyphen.";
  if (/--/.test(slug)) return "Slug cannot contain consecutive hyphens.";
  return null;
}

export function ProjectsPage() {
  const { listProjects, createProject } = useApi();
  const navigate = useNavigate();

  const fetcher = useCallback(() => listProjects(), [listProjects]);
  const { data: projects, loading, error, refetch } = useFetch(fetcher);

  const [showCreate, setShowCreate] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [slugEdited, setSlugEdited] = useState(false);
  const [form, setForm] = useState<CreateProjectRequest>({ name: "", slug: "" });

  const slugError = validateSlug(form.slug);
  const canSubmit = !saving && form.name.trim() !== "" && form.slug !== "" && slugError === null;

  function handleNameChange(name: string) {
    setForm((prev) => ({
      ...prev,
      name,
      // Keep auto-deriving the slug until the user manually edits it
      slug: slugEdited ? prev.slug : nameToSlug(name),
    }));
  }

  function handleSlugChange(raw: string) {
    setSlugEdited(true);
    // Normalise as they type: lowercase and spaces→hyphens, but leave
    // other invalid chars visible so validateSlug can show a clear error.
    setForm((prev) => ({ ...prev, slug: raw.toLowerCase().replace(/\s+/g, "-") }));
  }

  function resetForm() {
    setForm({ name: "", slug: "" });
    setSlugEdited(false);
    setCreateError(null);
  }

  async function handleCreate() {
    if (!canSubmit) return;
    setSaving(true);
    setCreateError(null);
    try {
      const project = await createProject(form);
      refetch();
      setShowCreate(false);
      resetForm();
      navigate(`/projects/${project.id}/surveys`);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Failed to create project.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Projects</h1>
        <Button variant="primary" onClick={() => setShowCreate(true)}>
          + New Project
        </Button>
      </div>

      {loading && <Spinner />}
      {error && <div className="error-banner">{error}</div>}

      {projects && (
        projects.length === 0 ? (
          <div className="empty-state">No projects yet. Create your first project.</div>
        ) : (
          <div className="surveys-grid">
            {projects.map((p) => (
              <div
                key={p.id}
                className="survey-card"
                onClick={() => navigate(`/projects/${p.id}/surveys`)}
                style={{ cursor: "pointer" }}
              >
                <div className="survey-card-title">{p.name}</div>
                <div className="survey-card-meta">{p.slug}</div>
              </div>
            ))}
          </div>
        )
      )}

      <Modal
        open={showCreate}
        onClose={() => { setShowCreate(false); resetForm(); }}
        title="New Project"
        footer={
          <>
            <Button variant="ghost" onClick={() => { setShowCreate(false); resetForm(); }}>
              Cancel
            </Button>
            <Button variant="primary" onClick={handleCreate} disabled={!canSubmit}>
              {saving ? "Creating…" : "Create"}
            </Button>
          </>
        }
      >
        {createError && <div className="error-banner">{createError}</div>}
        <Input
          label="Name"
          value={form.name}
          onChange={(e) => handleNameChange(e.target.value)}
          placeholder="My Project"
          autoFocus
        />
        <Input
          label="URL-safe name"
          value={form.slug}
          onChange={(e) => handleSlugChange(e.target.value)}
          placeholder="my-project"
          hint={!slugEdited && form.name ? "Auto-generated from name — you can edit this." : "Used in URLs: /projects/{url-safe-name}"}
          error={slugError ?? undefined}
        />
      </Modal>
    </div>
  );
}
