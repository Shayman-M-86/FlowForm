import { useCallback, useState } from "react";
import {
  createScoringRule,
  deleteScoringRule,
  listScoringRules,
  updateScoringRule,
} from "../../api/content";
import type { CreateScoringRuleRequest, ScoringRuleOut } from "../../api/types";
import { useFetch } from "../../hooks/useFetch";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Modal } from "../ui/Modal";
import { Spinner } from "../ui/Spinner";
import "../../App.css";
import "./RuleList.css";

interface ScoringRuleListProps {
  projectId: number;
  surveyId: number;
  versionId: number;
  readOnly?: boolean;
}

export function ScoringRuleList({
  projectId,
  surveyId,
  versionId,
  readOnly,
}: ScoringRuleListProps) {
  const fetcher = useCallback(
    () => listScoringRules(projectId, surveyId, versionId),
    [projectId, surveyId, versionId],
  );
  const { data: rules, loading, error, refetch } = useFetch(fetcher);

  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<ScoringRuleOut | null>(null);
  const [scoringKey, setScoringKey] = useState("");
  const [schemaText, setSchemaText] = useState("{}");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function openAdd() {
    setEditing(null);
    setScoringKey("");
    setSchemaText("{}");
    setSaveError(null);
    setEditorOpen(true);
  }

  function openEdit(r: ScoringRuleOut) {
    setEditing(r);
    setScoringKey(r.scoring_key);
    setSchemaText(JSON.stringify(r.scoring_schema, null, 2));
    setSaveError(null);
    setEditorOpen(true);
  }

  async function handleSave() {
    let schema: Record<string, unknown>;
    try {
      schema = JSON.parse(schemaText) as Record<string, unknown>;
    } catch {
      setSaveError("Invalid JSON in scoring schema.");
      return;
    }
    if (!scoringKey.trim()) { setSaveError("Scoring key is required."); return; }
    setSaving(true);
    setSaveError(null);
    try {
      const data: CreateScoringRuleRequest = {
        scoring_key: scoringKey.trim(),
        scoring_schema: schema,
      };
      if (editing) {
        await updateScoringRule(projectId, surveyId, versionId, editing.id, data);
      } else {
        await createScoringRule(projectId, surveyId, versionId, data);
      }
      refetch();
      setEditorOpen(false);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to save scoring rule.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(r: ScoringRuleOut) {
    if (!confirm(`Delete scoring rule "${r.scoring_key}"?`)) return;
    await deleteScoringRule(projectId, surveyId, versionId, r.id);
    refetch();
  }

  if (loading) return <Spinner />;
  if (error) return <div className="error-banner">{error}</div>;

  return (
    <div>
      {rules?.length === 0 ? (
        <div className="empty-state">No scoring rules yet.</div>
      ) : (
        <div className="item-list">
          {rules?.map((r) => (
            <div key={r.id} className="item-list__row">
              <div className="item-list__main">
                <code>{r.scoring_key}</code>
              </div>
              {!readOnly && (
                <div className="item-list__actions">
                  <Button size="sm" variant="ghost" onClick={() => openEdit(r)}>
                    Edit
                  </Button>
                  <Button size="sm" variant="danger" onClick={() => handleDelete(r)}>
                    Delete
                  </Button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {!readOnly && (
        <div style={{ marginTop: 14 }}>
          <Button variant="secondary" onClick={openAdd}>
            + Add Scoring Rule
          </Button>
        </div>
      )}

      <Modal
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        title={editing ? "Edit Scoring Rule" : "Add Scoring Rule"}
        width={540}
        footer={
          <>
            <Button variant="ghost" onClick={() => setEditorOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={handleSave} disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </>
        }
      >
        {saveError && <div className="error-banner">{saveError}</div>}
        <Input
          label="Scoring key"
          value={scoringKey}
          onChange={(e) => setScoringKey(e.target.value)}
          placeholder="risk_score"
          disabled={!!editing}
        />
        <div className="rule-schema-field">
          <label className="rule-schema-label">Scoring schema (JSON)</label>
          <textarea
            className="rule-schema-textarea"
            value={schemaText}
            onChange={(e) => setSchemaText(e.target.value)}
            rows={8}
            spellCheck={false}
          />
        </div>
      </Modal>
    </div>
  );
}
