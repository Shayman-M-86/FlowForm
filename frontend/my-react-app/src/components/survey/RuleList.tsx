import { useCallback, useState } from "react";
import { useApi } from "../../api/useApi";
import type { CreateRuleRequest, RuleOut } from "../../api/types";
import { useFetch } from "../../hooks/useFetch";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Modal } from "../ui/Modal";
import { Select } from "../ui/Select";
import { Spinner } from "../ui/Spinner";
import "../../App.css";
import "./RuleList.css";

// ── Types ─────────────────────────────────────────────────────────────────────

type ConditionMode = "simple" | "all" | "any" | "not";
type EffectValue   = "unset" | "true" | "false";

interface SimpleCond {
  fact:     string;
  operator: string;
  value:    string;
}

function defaultSimple(): SimpleCond {
  return { fact: "answers.", operator: "equals", value: "" };
}

interface RuleEditorState {
  target:        string;
  sortOrder:     string;
  conditionMode: ConditionMode;
  simple:        SimpleCond;
  conditions:    SimpleCond[];
  effects: {
    visible:  EffectValue;
    required: EffectValue;
    disabled: EffectValue;
  };
}

function defaultEditorState(): RuleEditorState {
  return {
    target:        "",
    sortOrder:     "",
    conditionMode: "simple",
    simple:        defaultSimple(),
    conditions:    [defaultSimple()],
    effects:       { visible: "unset", required: "unset", disabled: "unset" },
  };
}

// ── Constants ─────────────────────────────────────────────────────────────────

const CONDITION_MODE_OPTIONS = [
  { value: "simple", label: "Simple condition" },
  { value: "all",    label: "All of (AND)" },
  { value: "any",    label: "Any of (OR)" },
  { value: "not",    label: "NOT" },
];

const OPERATOR_OPTIONS = [
  { value: "equals",       label: "equals" },
  { value: "not_equals",   label: "not equals" },
  { value: "is_answered",  label: "is answered" },
  { value: "is_empty",     label: "is empty" },
  { value: "contains",     label: "contains" },
  { value: "contains_any", label: "contains any (comma-separated)" },
  { value: "contains_all", label: "contains all (comma-separated)" },
  { value: "gt",           label: "greater than" },
  { value: "gte",          label: "greater than or equal" },
  { value: "lt",           label: "less than" },
  { value: "lte",          label: "less than or equal" },
  { value: "between",      label: "between (min,max)" },
];

const EFFECT_OPTIONS = [
  { value: "unset", label: "— not set —" },
  { value: "true",  label: "true" },
  { value: "false", label: "false" },
];

const NO_VALUE_OPERATORS = new Set(["is_answered", "is_empty"]);
const ARRAY_OPERATORS    = new Set(["contains_any", "contains_all"]);

// ── Helpers ───────────────────────────────────────────────────────────────────

function buildSimpleCond(s: SimpleCond): Record<string, unknown> {
  if (NO_VALUE_OPERATORS.has(s.operator)) {
    return { fact: s.fact, operator: s.operator };
  }
  if (ARRAY_OPERATORS.has(s.operator) || s.operator === "between") {
    const arr = s.value.split(",").map((v) => v.trim()).filter(Boolean);
    return { fact: s.fact, operator: s.operator, value: arr };
  }
  // Try numeric coercion for comparison operators
  const numericOps = new Set(["gt", "gte", "lt", "lte"]);
  if (numericOps.has(s.operator)) {
    const n = Number(s.value);
    return { fact: s.fact, operator: s.operator, value: isNaN(n) ? s.value : n };
  }
  return { fact: s.fact, operator: s.operator, value: s.value };
}

function buildCondition(state: RuleEditorState): Record<string, unknown> {
  switch (state.conditionMode) {
    case "simple": return buildSimpleCond(state.simple);
    case "not":    return { not: buildSimpleCond(state.simple) };
    case "all":    return { all: state.conditions.map(buildSimpleCond) };
    case "any":    return { any: state.conditions.map(buildSimpleCond) };
  }
}

function buildEffects(effects: RuleEditorState["effects"]): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(effects)) {
    if (v === "true")  out[k] = true;
    if (v === "false") out[k] = false;
  }
  return out;
}

function buildRuleSchema(state: RuleEditorState): Record<string, unknown> {
  const schema: Record<string, unknown> = {
    target:    state.target,
    condition: buildCondition(state),
    effects:   buildEffects(state.effects),
  };
  const so = Number(state.sortOrder);
  if (state.sortOrder !== "" && !isNaN(so)) schema.sort_order = so;
  return schema;
}

function parseEditorState(rs: Record<string, unknown>): RuleEditorState {
  const state = defaultEditorState();
  state.target    = (rs.target    as string) ?? "";
  state.sortOrder = rs.sort_order != null ? String(rs.sort_order) : "";

  // parse effects
  const e = (rs.effects as Record<string, unknown>) ?? {};
  for (const k of ["visible", "required", "disabled"] as const) {
    if (k in e) state.effects[k] = e[k] === true ? "true" : "false";
  }

  // parse condition
  const cond = (rs.condition as Record<string, unknown>) ?? {};
  if ("all" in cond) {
    state.conditionMode = "all";
    state.conditions = ((cond.all as Record<string, unknown>[]) ?? []).map(parseSimple);
  } else if ("any" in cond) {
    state.conditionMode = "any";
    state.conditions = ((cond.any as Record<string, unknown>[]) ?? []).map(parseSimple);
  } else if ("not" in cond) {
    state.conditionMode = "not";
    state.simple = parseSimple((cond.not as Record<string, unknown>) ?? {});
  } else {
    state.conditionMode = "simple";
    state.simple = parseSimple(cond);
  }
  return state;
}

function parseSimple(c: Record<string, unknown>): SimpleCond {
  const val = c.value;
  let valueStr = "";
  if (Array.isArray(val)) valueStr = val.join(", ");
  else if (val != null)   valueStr = String(val);
  return {
    fact:     (c.fact     as string) ?? "answers.",
    operator: (c.operator as string) ?? "equals",
    value:    valueStr,
  };
}

// ── Sub-components ────────────────────────────────────────────────────────────

interface SimpleCondEditorProps {
  cond:     SimpleCond;
  onChange: (c: SimpleCond) => void;
}

function SimpleCondEditor({ cond, onChange }: SimpleCondEditorProps) {
  const noValue = NO_VALUE_OPERATORS.has(cond.operator);
  return (
    <div className="rule-cond-simple">
      <Input
        label="Fact"
        value={cond.fact}
        onChange={(e) => onChange({ ...cond, fact: e.target.value })}
        placeholder="answers.q1"
        hint='Format: answers.<question_key>'
      />
      <Select
        label="Operator"
        options={OPERATOR_OPTIONS}
        value={cond.operator}
        onChange={(e) => onChange({ ...cond, operator: e.target.value, value: "" })}
      />
      {!noValue && (
        <Input
          label="Value"
          value={cond.value}
          onChange={(e) => onChange({ ...cond, value: e.target.value })}
          placeholder={
            ARRAY_OPERATORS.has(cond.operator) || cond.operator === "between"
              ? "comma-separated, e.g. a1, a2"
              : "e.g. a2"
          }
        />
      )}
    </div>
  );
}

// ── Rule editor modal form ────────────────────────────────────────────────────

interface RuleEditorFormProps {
  state:     RuleEditorState;
  onChange:  (s: RuleEditorState) => void;
}

function RuleEditorForm({ state, onChange }: RuleEditorFormProps) {
  function set<K extends keyof RuleEditorState>(k: K, v: RuleEditorState[K]) {
    onChange({ ...state, [k]: v });
  }

  function setEffect(k: keyof RuleEditorState["effects"], v: EffectValue) {
    onChange({ ...state, effects: { ...state.effects, [k]: v } });
  }

  function setCond(i: number, c: SimpleCond) {
    const next = [...state.conditions]; next[i] = c;
    onChange({ ...state, conditions: next });
  }
  function addCond() {
    onChange({ ...state, conditions: [...state.conditions, defaultSimple()] });
  }
  function removeCond(i: number) {
    onChange({ ...state, conditions: state.conditions.filter((_, idx) => idx !== i) });
  }

  return (
    <>
      <Input
        label="Target (question key)"
        value={state.target}
        onChange={(e) => set("target", e.target.value)}
        placeholder="q3"
        hint="The question this rule acts on."
      />
      <Input
        label="Sort order (optional)"
        type="number"
        value={state.sortOrder}
        onChange={(e) => set("sortOrder", e.target.value)}
        placeholder="20"
        hint="Ascending sort; later matching rules override earlier ones."
      />

      <div className="rule-section">
        <div className="rule-section-label">Condition</div>
        <Select
          label="Condition type"
          options={CONDITION_MODE_OPTIONS}
          value={state.conditionMode}
          onChange={(e) => set("conditionMode", e.target.value as ConditionMode)}
        />

        {(state.conditionMode === "simple" || state.conditionMode === "not") && (
          <SimpleCondEditor
            cond={state.simple}
            onChange={(c) => set("simple", c)}
          />
        )}

        {(state.conditionMode === "all" || state.conditionMode === "any") && (
          <div className="rule-cond-group">
            {state.conditions.map((c, i) => (
              <div key={i} className="rule-cond-group__item">
                <SimpleCondEditor cond={c} onChange={(nc) => setCond(i, nc)} />
                {state.conditions.length > 1 && (
                  <Button size="sm" variant="ghost" onClick={() => removeCond(i)}>
                    Remove
                  </Button>
                )}
              </div>
            ))}
            <Button size="sm" variant="secondary" onClick={addCond}>+ Add condition</Button>
          </div>
        )}
      </div>

      <div className="rule-section">
        <div className="rule-section-label">Effects</div>
        <div className="rule-effects-grid">
          {(["visible", "required", "disabled"] as const).map((k) => (
            <Select
              key={k}
              label={k}
              options={EFFECT_OPTIONS}
              value={state.effects[k]}
              onChange={(e) => setEffect(k, e.target.value as EffectValue)}
            />
          ))}
        </div>
      </div>
    </>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface RuleListProps {
  projectId: number;
  surveyId:  number;
  versionId: number;
  readOnly?: boolean;
}

export function RuleList({ projectId, surveyId, versionId, readOnly }: RuleListProps) {
  const api = useApi();
  const fetcher = useCallback(
    () => api.listRules(projectId, surveyId, versionId),
    [api, projectId, surveyId, versionId],
  );
  const { data: rules, loading, error, refetch } = useFetch(fetcher);

  const [editorOpen, setEditorOpen] = useState(false);
  const [editing,    setEditing]    = useState<RuleOut | null>(null);
  const [ruleKey,    setRuleKey]    = useState("");
  const [editorState, setEditorState] = useState<RuleEditorState>(defaultEditorState);
  const [saveError,  setSaveError]  = useState<string | null>(null);
  const [saving,     setSaving]     = useState(false);

  function openAdd() {
    setEditing(null);
    setRuleKey("");
    setEditorState(defaultEditorState());
    setSaveError(null);
    setEditorOpen(true);
  }

  function openEdit(r: RuleOut) {
    setEditing(r);
    setRuleKey(r.rule_key);
    setEditorState(parseEditorState(r.rule_schema as Record<string, unknown>));
    setSaveError(null);
    setEditorOpen(true);
  }

  async function handleSave() {
    if (!ruleKey.trim()) { setSaveError("Rule key is required."); return; }
    if (!editorState.target.trim()) { setSaveError("Target question key is required."); return; }

    const effects = buildEffects(editorState.effects);
    if (Object.keys(effects).length === 0) {
      setSaveError("At least one effect (visible, required, or disabled) must be set.");
      return;
    }

    setSaving(true);
    setSaveError(null);
    try {
      const data: CreateRuleRequest = {
        rule_key:   ruleKey.trim(),
        rule_schema: buildRuleSchema(editorState),
      };
      if (editing) {
        await api.updateRule(projectId, surveyId, versionId, editing.id, data);
      } else {
        await api.createRule(projectId, surveyId, versionId, data);
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
    await api.deleteRule(projectId, surveyId, versionId, r.id);
    refetch();
  }

  if (loading) return <Spinner />;
  if (error)   return <div className="error-banner">{error}</div>;

  return (
    <div>
      {rules?.length === 0 ? (
        <div className="empty-state">No rules yet.</div>
      ) : (
        <div className="item-list">
          {rules?.map((r) => {
            const rs = r.rule_schema as Record<string, unknown>;
            return (
              <div key={r.id} className="item-list__row">
                <div className="item-list__main">
                  <code>{r.rule_key}</code>
                  {rs.target ? (
                    <span className="rule-meta">→ {String(rs.target)}</span>
                  ) : null}
                </div>
                {!readOnly && (
                  <div className="item-list__actions">
                    <Button size="sm" variant="ghost" onClick={() => openEdit(r)}>Edit</Button>
                    <Button size="sm" variant="danger" onClick={() => handleDelete(r)}>Delete</Button>
                  </div>
                )}
              </div>
            );
          })}
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
        width={560}
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
          placeholder="show_q3_when_q1_is_yes"
          disabled={!!editing}
        />
        <RuleEditorForm state={editorState} onChange={setEditorState} />
      </Modal>
    </div>
  );
}
