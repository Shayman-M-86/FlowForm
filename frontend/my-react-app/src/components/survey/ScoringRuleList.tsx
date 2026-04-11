import { useCallback, useState } from "react";
import { useApi } from "../../api/useApi";
import type { CreateScoringRuleRequest, ScoringRuleOut } from "../../api/types";
import { useFetch } from "../../hooks/useFetch";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Modal } from "../ui/Modal";
import { Select } from "../ui/Select";
import { Spinner } from "../ui/Spinner";
import "../../App.css";
import "./RuleList.css";
import "./ScoringRuleList.css";

// ── Types ─────────────────────────────────────────────────────────────────────

type Strategy =
  | "choice_option_map"
  | "matching_answer_key"
  | "rating_direct"
  | "field_numeric_ranges";

interface OptionScore   { id: string; score: string }
interface CorrectPair   { left_id: string; right_id: string }
interface NumericRange  { min: string; max: string; score: string }

interface ScoringEditorState {
  target:         string;
  bucket:         string;
  strategy:       Strategy;
  conditionJson:  string;  // optional condition as raw JSON (null → "")
  // strategy-specific config
  optionScores:   OptionScore[];
  combine:        "sum" | "max";
  correctPairs:   CorrectPair[];
  pointsPerCorrect:      string;
  penaltyPerIncorrect:   string;
  maxScore:              string;
  multiplier:     string;
  ranges:         NumericRange[];
}

function defaultEditorState(): ScoringEditorState {
  return {
    target:              "",
    bucket:              "total",
    strategy:            "rating_direct",
    conditionJson:       "",
    optionScores:        [{ id: "", score: "" }],
    combine:             "sum",
    correctPairs:        [{ left_id: "", right_id: "" }],
    pointsPerCorrect:    "1",
    penaltyPerIncorrect: "0",
    maxScore:            "",
    multiplier:          "1",
    ranges:              [{ min: "", max: "", score: "" }],
  };
}

// ── Constants ─────────────────────────────────────────────────────────────────

const STRATEGY_OPTIONS = [
  { value: "rating_direct",      label: "Rating — direct value (rating_direct)" },
  { value: "choice_option_map",  label: "Choice — option score map (choice_option_map)" },
  { value: "matching_answer_key",label: "Matching — answer key (matching_answer_key)" },
  { value: "field_numeric_ranges", label: "Field — numeric ranges (field_numeric_ranges)" },
];

const COMBINE_OPTIONS = [
  { value: "sum", label: "Sum" },
  { value: "max", label: "Max" },
];

// ── Build scoring_schema from editor state ────────────────────────────────────

function buildConfig(state: ScoringEditorState): Record<string, unknown> {
  switch (state.strategy) {
    case "choice_option_map": {
      const option_scores: Record<string, number> = {};
      for (const os of state.optionScores) {
        if (os.id.trim()) option_scores[os.id.trim()] = Number(os.score) || 0;
      }
      return { option_scores, combine: state.combine };
    }
    case "matching_answer_key": {
      const correct_pairs = state.correctPairs
        .filter((p) => p.left_id.trim() && p.right_id.trim())
        .map((p) => ({ left_id: p.left_id.trim(), right_id: p.right_id.trim() }));
      const out: Record<string, unknown> = {
        correct_pairs,
        points_per_correct:    Number(state.pointsPerCorrect)    || 1,
        penalty_per_incorrect: Number(state.penaltyPerIncorrect) || 0,
      };
      if (state.maxScore.trim()) out.max_score = Number(state.maxScore);
      return out;
    }
    case "rating_direct":
      return { multiplier: Number(state.multiplier) || 1 };
    case "field_numeric_ranges": {
      const ranges = state.ranges
        .filter((r) => r.min.trim() && r.max.trim())
        .map((r) => ({ min: Number(r.min), max: Number(r.max), score: Number(r.score) || 0 }));
      return { ranges };
    }
  }
}

function buildScoringSchema(state: ScoringEditorState): Record<string, unknown> {
  let condition: unknown = null;
  if (state.conditionJson.trim()) {
    try { condition = JSON.parse(state.conditionJson); } catch { /* ignore */ }
  }
  return {
    target:    state.target,
    bucket:    state.bucket,
    strategy:  state.strategy,
    config:    buildConfig(state),
    condition,
  };
}

function parseEditorState(ss: Record<string, unknown>): ScoringEditorState {
  const state = defaultEditorState();
  state.target   = (ss.target   as string) ?? "";
  state.bucket   = (ss.bucket   as string) ?? "total";
  state.strategy = (ss.strategy as Strategy) ?? "rating_direct";
  if (ss.condition != null) {
    state.conditionJson = JSON.stringify(ss.condition, null, 2);
  }

  const cfg = (ss.config as Record<string, unknown>) ?? {};

  switch (state.strategy) {
    case "choice_option_map": {
      const os = (cfg.option_scores as Record<string, number>) ?? {};
      state.optionScores = Object.entries(os).map(([id, score]) => ({ id, score: String(score) }));
      if (state.optionScores.length === 0) state.optionScores = [{ id: "", score: "" }];
      state.combine = ((cfg.combine as string) ?? "sum") as "sum" | "max";
      break;
    }
    case "matching_answer_key": {
      const cp = (cfg.correct_pairs as { left_id: string; right_id: string }[]) ?? [];
      state.correctPairs        = cp.length ? cp : [{ left_id: "", right_id: "" }];
      state.pointsPerCorrect    = String(cfg.points_per_correct    ?? 1);
      state.penaltyPerIncorrect = String(cfg.penalty_per_incorrect ?? 0);
      state.maxScore            = cfg.max_score != null ? String(cfg.max_score) : "";
      break;
    }
    case "rating_direct":
      state.multiplier = String(cfg.multiplier ?? 1);
      break;
    case "field_numeric_ranges": {
      const rs = (cfg.ranges as { min: number; max: number; score: number }[]) ?? [];
      state.ranges = rs.length
        ? rs.map((r) => ({ min: String(r.min), max: String(r.max), score: String(r.score) }))
        : [{ min: "", max: "", score: "" }];
      break;
    }
  }

  return state;
}

// ── Strategy-specific config editors ─────────────────────────────────────────

interface ConfigEditorProps {
  state:    ScoringEditorState;
  onChange: (s: ScoringEditorState) => void;
}

function ChoiceOptionMapConfig({ state, onChange }: ConfigEditorProps) {
  function setRow(i: number, field: keyof OptionScore, v: string) {
    const next = [...state.optionScores]; next[i] = { ...next[i], [field]: v };
    onChange({ ...state, optionScores: next });
  }
  function addRow() {
    onChange({ ...state, optionScores: [...state.optionScores, { id: "", score: "" }] });
  }
  function removeRow(i: number) {
    onChange({ ...state, optionScores: state.optionScores.filter((_, idx) => idx !== i) });
  }
  return (
    <>
      <div className="scoring-section">
        <div className="scoring-section-label">Option scores</div>
        {state.optionScores.map((os, i) => (
          <div key={i} className="scoring-row">
            <Input
              placeholder="Option ID (e.g. a1)"
              value={os.id}
              onChange={(e) => setRow(i, "id", e.target.value)}
            />
            <Input
              placeholder="Score"
              type="number"
              value={os.score}
              onChange={(e) => setRow(i, "score", e.target.value)}
            />
            {state.optionScores.length > 1 && (
              <Button size="sm" variant="ghost" onClick={() => removeRow(i)}>✕</Button>
            )}
          </div>
        ))}
        <Button size="sm" variant="secondary" onClick={addRow}>+ Add option</Button>
      </div>
      <Select
        label="Combine"
        options={COMBINE_OPTIONS}
        value={state.combine}
        onChange={(e) => onChange({ ...state, combine: e.target.value as "sum" | "max" })}
      />
    </>
  );
}

function MatchingAnswerKeyConfig({ state, onChange }: ConfigEditorProps) {
  function setRow(i: number, field: keyof CorrectPair, v: string) {
    const next = [...state.correctPairs]; next[i] = { ...next[i], [field]: v };
    onChange({ ...state, correctPairs: next });
  }
  function addRow() {
    onChange({ ...state, correctPairs: [...state.correctPairs, { left_id: "", right_id: "" }] });
  }
  function removeRow(i: number) {
    onChange({ ...state, correctPairs: state.correctPairs.filter((_, idx) => idx !== i) });
  }
  return (
    <>
      <div className="scoring-section">
        <div className="scoring-section-label">Correct pairs</div>
        {state.correctPairs.map((cp, i) => (
          <div key={i} className="scoring-row">
            <Input
              placeholder="Left ID (e.g. c1)"
              value={cp.left_id}
              onChange={(e) => setRow(i, "left_id", e.target.value)}
            />
            <Input
              placeholder="Right ID (e.g. r1)"
              value={cp.right_id}
              onChange={(e) => setRow(i, "right_id", e.target.value)}
            />
            {state.correctPairs.length > 1 && (
              <Button size="sm" variant="ghost" onClick={() => removeRow(i)}>✕</Button>
            )}
          </div>
        ))}
        <Button size="sm" variant="secondary" onClick={addRow}>+ Add pair</Button>
      </div>
      <div className="scoring-inline">
        <Input
          label="Points per correct"
          type="number"
          value={state.pointsPerCorrect}
          onChange={(e) => onChange({ ...state, pointsPerCorrect: e.target.value })}
        />
        <Input
          label="Penalty per incorrect"
          type="number"
          value={state.penaltyPerIncorrect}
          onChange={(e) => onChange({ ...state, penaltyPerIncorrect: e.target.value })}
        />
        <Input
          label="Max score (optional)"
          type="number"
          value={state.maxScore}
          onChange={(e) => onChange({ ...state, maxScore: e.target.value })}
          placeholder="—"
        />
      </div>
    </>
  );
}

function RatingDirectConfig({ state, onChange }: ConfigEditorProps) {
  return (
    <Input
      label="Multiplier"
      type="number"
      value={state.multiplier}
      onChange={(e) => onChange({ ...state, multiplier: e.target.value })}
      placeholder="1"
    />
  );
}

function FieldNumericRangesConfig({ state, onChange }: ConfigEditorProps) {
  function setRow(i: number, field: keyof NumericRange, v: string) {
    const next = [...state.ranges]; next[i] = { ...next[i], [field]: v };
    onChange({ ...state, ranges: next });
  }
  function addRow() {
    onChange({ ...state, ranges: [...state.ranges, { min: "", max: "", score: "" }] });
  }
  function removeRow(i: number) {
    onChange({ ...state, ranges: state.ranges.filter((_, idx) => idx !== i) });
  }
  return (
    <div className="scoring-section">
      <div className="scoring-section-label">Ranges</div>
      {state.ranges.map((r, i) => (
        <div key={i} className="scoring-row scoring-row--triple">
          <Input
            placeholder="Min"
            type="number"
            value={r.min}
            onChange={(e) => setRow(i, "min", e.target.value)}
          />
          <Input
            placeholder="Max"
            type="number"
            value={r.max}
            onChange={(e) => setRow(i, "max", e.target.value)}
          />
          <Input
            placeholder="Score"
            type="number"
            value={r.score}
            onChange={(e) => setRow(i, "score", e.target.value)}
          />
          {state.ranges.length > 1 && (
            <Button size="sm" variant="ghost" onClick={() => removeRow(i)}>✕</Button>
          )}
        </div>
      ))}
      <Button size="sm" variant="secondary" onClick={addRow}>+ Add range</Button>
    </div>
  );
}

function ConfigEditor({ state, onChange }: ConfigEditorProps) {
  switch (state.strategy) {
    case "choice_option_map":   return <ChoiceOptionMapConfig   state={state} onChange={onChange} />;
    case "matching_answer_key": return <MatchingAnswerKeyConfig state={state} onChange={onChange} />;
    case "rating_direct":       return <RatingDirectConfig      state={state} onChange={onChange} />;
    case "field_numeric_ranges":return <FieldNumericRangesConfig state={state} onChange={onChange} />;
  }
}

// ── Main component ────────────────────────────────────────────────────────────

interface ScoringRuleListProps {
  projectId: number;
  surveyId:  number;
  versionNumber: number;
  readOnly?: boolean;
}

export function ScoringRuleList({
  projectId,
  surveyId,
  versionNumber,
  readOnly,
}: ScoringRuleListProps) {
  const api = useApi();
  const fetcher = useCallback(
    () => api.listScoringRules(projectId, surveyId, versionNumber),
    [api, projectId, surveyId, versionNumber],
  );
  const { data: rules, loading, error, refetch } = useFetch(fetcher, [
    projectId,
    surveyId,
    versionNumber,
  ]);

  const [editorOpen,   setEditorOpen]   = useState(false);
  const [editing,      setEditing]      = useState<ScoringRuleOut | null>(null);
  const [scoringKey,   setScoringKey]   = useState("");
  const [editorState,  setEditorState]  = useState<ScoringEditorState>(defaultEditorState);
  const [saveError,    setSaveError]    = useState<string | null>(null);
  const [saving,       setSaving]       = useState(false);

  function openAdd() {
    setEditing(null);
    setScoringKey("");
    setEditorState(defaultEditorState());
    setSaveError(null);
    setEditorOpen(true);
  }

  function openEdit(r: ScoringRuleOut) {
    setEditing(r);
    setScoringKey(r.scoring_key);
    setEditorState(parseEditorState(r.scoring_schema as Record<string, unknown>));
    setSaveError(null);
    setEditorOpen(true);
  }

  async function handleSave() {
    if (!scoringKey.trim())      { setSaveError("Scoring key is required.");        return; }
    if (!editorState.target.trim()) { setSaveError("Target question key is required."); return; }
    if (!editorState.bucket.trim()) { setSaveError("Bucket is required.");            return; }

    // Validate optional condition JSON
    if (editorState.conditionJson.trim()) {
      try { JSON.parse(editorState.conditionJson); } catch {
        setSaveError("Condition JSON is invalid."); return;
      }
    }

    setSaving(true);
    setSaveError(null);
    try {
      const data: CreateScoringRuleRequest = {
        scoring_key:    scoringKey.trim(),
        scoring_schema: buildScoringSchema(editorState),
      };
      if (editing) {
        await api.updateScoringRule(projectId, surveyId, versionNumber, editing.id, data);
      } else {
        await api.createScoringRule(projectId, surveyId, versionNumber, data);
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
    await api.deleteScoringRule(projectId, surveyId, versionNumber, r.id);
    refetch();
  }

  if (loading) return <Spinner />;
  if (error)   return <div className="error-banner">{error}</div>;

  return (
    <div>
      {rules?.length === 0 ? (
        <div className="empty-state">No scoring rules yet.</div>
      ) : (
        <div className="item-list">
          {rules?.map((r) => {
            const ss = r.scoring_schema as Record<string, unknown>;
            return (
              <div key={r.id} className="item-list__row">
                <div className="item-list__main">
                  <code>{r.scoring_key}</code>
                  {ss.target ? (
                    <span className="rule-meta">
                      → {String(ss.target)} · {String(ss.strategy)} · bucket: {String(ss.bucket)}
                    </span>
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
        <div className="stack-actions">
          <Button variant="secondary" onClick={openAdd}>+ Add Scoring Rule</Button>
        </div>
      )}

      <Modal
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        title={editing ? "Edit Scoring Rule" : "Add Scoring Rule"}
        width={580}
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
          label="Scoring key"
          value={scoringKey}
          onChange={(e) => setScoringKey(e.target.value)}
          placeholder="score_q_satisfaction"
          disabled={!!editing}
        />

        <div className="scoring-inline">
          <Input
            label="Target (question key)"
            value={editorState.target}
            onChange={(e) => setEditorState((s) => ({ ...s, target: e.target.value }))}
            placeholder="q_satisfaction"
          />
          <Input
            label="Bucket"
            value={editorState.bucket}
            onChange={(e) => setEditorState((s) => ({ ...s, bucket: e.target.value }))}
            placeholder="total"
          />
        </div>

        <Select
          label="Strategy"
          options={STRATEGY_OPTIONS}
          value={editorState.strategy}
          onChange={(e) =>
            setEditorState((s) => ({
              ...defaultEditorState(),
              scoringKey,
              target: s.target,
              bucket: s.bucket,
              strategy: e.target.value as Strategy,
            }))
          }
        />

        <div className="rule-section">
          <div className="rule-section-label">Config</div>
          <ConfigEditor state={editorState} onChange={setEditorState} />
        </div>

        <div className="rule-schema-field">
          <label className="rule-schema-label">
            Condition (optional JSON — uses same shape as rule conditions)
          </label>
          <textarea
            className="rule-schema-textarea"
            value={editorState.conditionJson}
            onChange={(e) => setEditorState((s) => ({ ...s, conditionJson: e.target.value }))}
            rows={4}
            spellCheck={false}
            placeholder='Leave blank for no condition, or enter e.g. {"fact":"answers.q1","operator":"equals","value":"yes"}'
          />
        </div>
      </Modal>
    </div>
  );
}
