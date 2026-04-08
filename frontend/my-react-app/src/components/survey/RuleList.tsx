import { useCallback, useState } from "react";
import { createRule, deleteRule, listRules, updateRule } from "../../api/content";
import type { CreateRuleRequest, RuleOut } from "../../api/types";
import { useFetch } from "../../hooks/useFetch";
import { Button } from "../ui/Button";
import { Modal } from "../ui/Modal";
import { Input } from "../ui/Input";
import { Spinner } from "../ui/Spinner";
import "../../App.css";
import "./RuleList.css";

interface RuleListProps {
  projectId: number;
  surveyId: number;
  versionId: number;
  readOnly?: boolean;
}

export function RuleList({ projectId, surveyId, versionId, readOnly }: RuleListProps) {
  const fetcher = useCallback(
    () => listRules(projectId, surveyId, versionId),
    [projectId, surveyId, versionId],
  );
  const { data: rules, loading, error, refetch } = useFetch(fetcher);

  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<RuleOut | null>(null);
  const [ruleKey, setRuleKey] = useState("");
  const [schemaText, setSchemaText] = useState("{}");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function openAdd() {
    setEditing(null);
    setRuleKey("");
    setSchemaText("{}");
    setSaveError(null);
    setEditorOpen(true);
  }

  function openEdit(r: RuleOut) {
    setEditing(r);
    setRuleKey(r.rule_key);
    setSchemaText(JSON.stringify(r.rule_schema, null, 2));
    setSaveError(null);
    setEditorOpen(true);
  }

  async function handleSave() {
    let schema: Record<string, unknown>;
    try {
      schema = JSON.parse(schemaText) as Record<string, unknown>;
    } catch {
      setSaveError("Invalid JSON in rule schema.");
      return;
    }
    if (!ruleKey.trim()) { setSaveError("Rule key is required."); return; }
    setSaving(true);
    setSaveError(null);
    try {
      const data: CreateRuleRequest = { rule_key: ruleKey.trim(), rule_schema: schema };
      if (editing) {
        await updateRule(projectId, surveyId, versionId, editing.id, data);
      } else {
        await createRule(projectId, surveyId, versionId, data);
      }
      refetch();
      setEditorOpen(false);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to save rule.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(r: RuleOut) {
    if (!confirm(`Delete rule "${r.rule_key}"?`)) return;
    await deleteRule(projectId, surveyId, versionId, r.id);
    refetch();
  }

  if (loading) return <Spinner />;
  if (error) return <div className="error-banner">{error}</div>;

  return (
    <div>
      {rules?.length === 0 ? (
        <div className="empty-state">No rules yet.</div>
      ) : (
        <div className="item-list">
          {rules?.map((r) => (
            <div key={r.id} className="item-list__row">
              <div className="item-list__main">
                <code>{r.rule_key}</code>
              </div>
              {!readOnly && (
                <div className="item-list__actions">
                  <Button size="sm" variant="ghost" onClick={() => openEdit(r)}>Edit</Button>
                  <Button size="sm" variant="danger" onClick={() => handleDelete(r)}>Delete</Button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {!readOnly && (
        <div style={{ marginTop: 14 }}>
          <Button variant="secondary" onClick={openAdd}>+ Add Rule</Button>
        </div>
      )}

      <Modal
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        title={editing ? "Edit Rule" : "Add Rule"}
        width={540}
        footer={
          <>
            <Button variant="ghost" onClick={() => setEditorOpen(false)}>Cancel</Button>
            <Button variant="primary" onClick={handleSave} disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </>
        }
      >
        {saveError && <div className="error-banner">{saveError}</div>}
        <Input
          label="Rule key"
          value={ruleKey}
          onChange={(e) => setRuleKey(e.target.value)}
          placeholder="eligibility_check"
          disabled={!!editing}
        />
        <div className="rule-schema-field">
          <label className="rule-schema-label">Rule schema (JSON)</label>
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
