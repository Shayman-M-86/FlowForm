import { useCallback, useState } from "react";
import { useApi } from "../../api/useApi";
import type { CreatePublicLinkOut } from "../../api/types";
import { useFetch } from "../../hooks/useFetch";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Modal } from "../ui/Modal";
import { Spinner } from "../ui/Spinner";
import { Toggle } from "../ui/Toggle";
import "../../App.css";
import "./PublicLinkList.css";

interface PublicLinkListProps {
  projectId: number;
  surveyId: number;
}

export function PublicLinkList({ projectId, surveyId }: PublicLinkListProps) {
  const api = useApi();
  const fetcher = useCallback(
    () => api.listPublicLinks(projectId, surveyId),
    [api, projectId, surveyId],
  );
  const { data, loading, error, refetch } = useFetch(fetcher, [projectId, surveyId]);

  const [createOpen, setCreateOpen] = useState(false);
  const [allowResponse, setAllowResponse] = useState(true);
  const [expiresAt, setExpiresAt] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // One-time token reveal
  const [revealResult, setRevealResult] = useState<CreatePublicLinkOut | null>(null);

  async function handleCreate() {
    setCreating(true);
    setCreateError(null);
    try {
      const result = await api.createPublicLink(projectId, surveyId, {
        allow_response: allowResponse,
        expires_at: expiresAt || null,
      });
      refetch();
      setCreateOpen(false);
      setRevealResult(result);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Failed to create link.");
    } finally {
      setCreating(false);
    }
  }

  async function handleToggleActive(linkId: number, current: boolean) {
    await api.updatePublicLink(projectId, surveyId, linkId, { is_active: !current });
    refetch();
  }

  async function handleDelete(linkId: number) {
    if (!confirm("Delete this public link?")) return;
    await api.deletePublicLink(projectId, surveyId, linkId);
    refetch();
  }

  if (loading) return <Spinner />;
  if (error) return <div className="error-banner">{error}</div>;

  const links = data?.links ?? [];

  return (
    <div>
      {links.length === 0 ? (
        <div className="empty-state">No public links yet.</div>
      ) : (
        <div className="item-list">
          {links.map((link) => (
            <div key={link.id} className="item-list__row">
              <div className="item-list__main">
                <div className="link-row__top">
                  <code className="link-prefix">{link.token_prefix}…</code>
                  <Badge variant={link.is_active ? "success" : "muted"}>
                    {link.is_active ? "active" : "inactive"}
                  </Badge>
                  {link.allow_response && <Badge variant="accent">responses on</Badge>}
                  {link.expires_at && (
                    <span className="link-expires">
                      Expires {new Date(link.expires_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
              <div className="item-list__actions">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleToggleActive(link.id, link.is_active)}
                >
                  {link.is_active ? "Deactivate" : "Activate"}
                </Button>
                <Button size="sm" variant="danger" onClick={() => handleDelete(link.id)}>
                  Delete
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="stack-actions">
        <Button variant="secondary" onClick={() => setCreateOpen(true)}>
          + Create Link
        </Button>
      </div>

      {/* Create link modal */}
      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Create Public Link"
        footer={
          <>
            <Button variant="ghost" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button variant="primary" onClick={handleCreate} disabled={creating}>
              {creating ? "Creating…" : "Create"}
            </Button>
          </>
        }
      >
        {createError && <div className="error-banner">{createError}</div>}
        <Toggle
          label="Allow responses"
          checked={allowResponse}
          onChange={setAllowResponse}
          hint="If off, the link resolves the survey but cannot submit answers."
        />
        <Input
          label="Expires at (optional)"
          type="datetime-local"
          value={expiresAt}
          onChange={(e) => setExpiresAt(e.target.value)}
          hint="Leave blank for no expiration."
        />
      </Modal>

      {/* One-time token reveal modal */}
      <Modal
        open={!!revealResult}
        onClose={() => setRevealResult(null)}
        title="Link Created — Save Token"
        footer={
          <Button variant="primary" onClick={() => setRevealResult(null)}>Done</Button>
        }
      >
        <p className="link-reveal__warning">
          The plaintext token is shown once. Copy it now — it cannot be retrieved again.
        </p>
        {revealResult && (
          <>
            <div className="link-reveal__field">
              <span className="link-reveal__label">Token</span>
              <code className="link-reveal__value">{revealResult.token}</code>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => navigator.clipboard.writeText(revealResult.token)}
              >
                Copy
              </Button>
            </div>
            <div className="link-reveal__field">
              <span className="link-reveal__label">URL</span>
              <code className="link-reveal__value link-reveal__value--url">{revealResult.url}</code>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => navigator.clipboard.writeText(revealResult.url)}
              >
                Copy
              </Button>
            </div>
          </>
        )}
      </Modal>
    </div>
  );
}
