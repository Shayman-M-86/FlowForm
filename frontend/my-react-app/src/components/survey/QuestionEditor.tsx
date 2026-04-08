import { useState } from "react";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Modal } from "../ui/Modal";
import { Select } from "../ui/Select";
import { Toggle } from "../ui/Toggle";
import type { CreateQuestionRequest, QuestionOut, QuestionType } from "../../api/types";
import "./QuestionEditor.css";

interface QuestionEditorProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: CreateQuestionRequest) => Promise<void>;
  initial?: QuestionOut;
}

const TYPE_OPTIONS = [
  { value: "choice", label: "Choice (multiple choice)" },
  { value: "field", label: "Field (text / number)" },
  { value: "rating", label: "Rating (scale)" },
  { value: "matching", label: "Matching (pairs)" },
];

const FIELD_TYPE_OPTIONS = [
  { value: "text", label: "Text" },
  { value: "number", label: "Number" },
  { value: "email", label: "Email" },
  { value: "date", label: "Date" },
];

function defaultSchema(type: QuestionType) {
  switch (type) {
    case "choice":
      return { type, label: "", required: false, options: [""] };
    case "field":
      return { type, label: "", required: false, field_type: "text" };
    case "rating":
      return { type, label: "", required: false, max: 5 };
    case "matching":
      return { type, label: "", required: false, pairs: [{ left: "", right: "" }] };
  }
}

export function QuestionEditor({ open, onClose, onSave, initial }: QuestionEditorProps) {
  const initType: QuestionType =
    (initial?.question_schema?.type as QuestionType) ?? "choice";

  const [key, setKey] = useState(initial?.question_key ?? "");
  const [type, setType] = useState<QuestionType>(initType);
  const [schema, setSchema] = useState<Record<string, unknown>>(
    initial?.question_schema ?? defaultSchema(initType),
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function changeType(t: QuestionType) {
    setType(t);
    setSchema(defaultSchema(t));
  }

  function setField<K extends keyof typeof schema>(k: K, v: unknown) {
    setSchema((prev) => ({ ...prev, [k]: v }));
  }

  // Options management (for choice type)
  const options = (schema.options as string[]) ?? [];
  function setOption(i: number, v: string) {
    const next = [...options];
    next[i] = v;
    setField("options", next);
  }
  function addOption() {
    setField("options", [...options, ""]);
  }
  function removeOption(i: number) {
    setField("options", options.filter((_, idx) => idx !== i));
  }

  // Pairs management (for matching type)
  const pairs = (schema.pairs as { left: string; right: string }[]) ?? [];
  function setPair(i: number, side: "left" | "right", v: string) {
    const next = [...pairs];
    next[i] = { ...next[i], [side]: v };
    setField("pairs", next);
  }
  function addPair() {
    setField("pairs", [...pairs, { left: "", right: "" }]);
  }
  function removePair(i: number) {
    setField("pairs", pairs.filter((_, idx) => idx !== i));
  }

  async function handleSave() {
    if (!key.trim()) { setError("Question key is required."); return; }
    setSaving(true);
    setError(null);
    try {
      await onSave({ question_key: key.trim(), question_schema: schema });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save question.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={initial ? "Edit Question" : "Add Question"}
      width={520}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={handleSave} disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </Button>
        </>
      }
    >
      {error && <div className="error-banner">{error}</div>}

      <Input
        label="Question key"
        value={key}
        onChange={(e) => setKey(e.target.value)}
        placeholder="q_name"
        hint="Snake_case identifier, unique per version."
        disabled={!!initial}
      />

      <Select
        label="Type"
        options={TYPE_OPTIONS}
        value={type}
        onChange={(e) => changeType(e.target.value as QuestionType)}
      />

      <Input
        label="Label"
        value={(schema.label as string) ?? ""}
        onChange={(e) => setField("label", e.target.value)}
        placeholder="What is your name?"
      />

      <Toggle
        label="Required"
        checked={(schema.required as boolean) ?? false}
        onChange={(v) => setField("required", v)}
      />

      {/* Type-specific fields */}
      {type === "choice" && (
        <div className="qe-section">
          <div className="qe-section-label">Options</div>
          {options.map((opt, i) => (
            <div key={i} className="qe-option-row">
              <Input
                value={opt}
                onChange={(e) => setOption(i, e.target.value)}
                placeholder={`Option ${i + 1}`}
              />
              {options.length > 1 && (
                <Button size="sm" variant="ghost" onClick={() => removeOption(i)}>✕</Button>
              )}
            </div>
          ))}
          <Button size="sm" variant="secondary" onClick={addOption}>+ Add option</Button>
        </div>
      )}

      {type === "field" && (
        <Select
          label="Field type"
          options={FIELD_TYPE_OPTIONS}
          value={(schema.field_type as string) ?? "text"}
          onChange={(e) => setField("field_type", e.target.value)}
        />
      )}

      {type === "rating" && (
        <Input
          label="Max rating"
          type="number"
          min={2}
          max={10}
          value={String((schema.max as number) ?? 5)}
          onChange={(e) => setField("max", Number(e.target.value))}
        />
      )}

      {type === "matching" && (
        <div className="qe-section">
          <div className="qe-section-label">Pairs</div>
          {pairs.map((pair, i) => (
            <div key={i} className="qe-pair-row">
              <Input
                value={pair.left}
                onChange={(e) => setPair(i, "left", e.target.value)}
                placeholder="Left"
              />
              <span className="qe-pair-arrow">→</span>
              <Input
                value={pair.right}
                onChange={(e) => setPair(i, "right", e.target.value)}
                placeholder="Right"
              />
              {pairs.length > 1 && (
                <Button size="sm" variant="ghost" onClick={() => removePair(i)}>✕</Button>
              )}
            </div>
          ))}
          <Button size="sm" variant="secondary" onClick={addPair}>+ Add pair</Button>
        </div>
      )}
    </Modal>
  );
}
