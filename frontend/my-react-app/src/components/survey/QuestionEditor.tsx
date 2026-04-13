import { useEffect, useState } from "react";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Modal } from "../ui/Modal";
import { Select } from "../ui/Select";
import { ApiRequestError } from "../../api/client";
import type { CreateQuestionRequest, QuestionOut, QuestionType } from "../../api/types";
import "./QuestionEditor.css";

interface QuestionEditorProps {
  open: boolean;
  onClose: () => void;
  onSave: (data: CreateQuestionRequest) => Promise<void>;
  initial?: QuestionOut;
}

const FIELD_LABELS: Record<string, string> = {
  "question_schema.label":                  "Question label",
  "question_schema.schema.max_selected":    "Max selected",
  "question_schema.schema.min_selected":    "Min selected",
  "question_schema.schema.field_type":      "Field type",
  "question_schema.schema.max":             "Max",
  "question_schema.schema.min":             "Min",
  "question_schema.schema.options":         "Options",
  "question_schema.schema.left_items":      "Left items",
  "question_schema.schema.right_items":     "Right items",
  "question_schema":                        "Question schema",
  "question_key":                           "Question key",
};

function friendlyError(field: string, message: string): string {
  // option/item label: question_schema.schema.options.N.label
  if (/^question_schema\.schema\.options\.\d+\.label$/.test(field)) return `Option label: ${message}`;
  if (/^question_schema\.schema\.options\.\d+\.id$/.test(field))    return `Option ID: ${message}`;
  if (/^question_schema\.schema\.left_items\.\d+/.test(field))      return `Left item: ${message}`;
  if (/^question_schema\.schema\.right_items\.\d+/.test(field))     return `Right item: ${message}`;
  const label = FIELD_LABELS[field];
  return label ? `${label}: ${message}` : message;
}

const FAMILY_OPTIONS = [
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

const CHOICE_STYLE_OPTIONS = [
  { value: "radio", label: "Radio (single select)" },
  { value: "checkbox", label: "Checkbox (multi select)" },
];

const RATING_STYLE_OPTIONS = [
  { value: "slider", label: "Slider" },
  { value: "stars", label: "Stars" },
  { value: "buttons", label: "Buttons" },
];

interface OptionItem { id: string; label: string }
interface MatchItem  { id: string; label: string }

function defaultQuestionSchema(family: QuestionType): Record<string, unknown> {
  switch (family) {
    case "choice":
      return {
        family: "choice",
        label: "",
        schema: { options: [{ id: "a1", label: "" }], min_selected: 1, max_selected: 1 },
        ui: { style: "radio" },
      };
    case "field":
      return {
        family: "field",
        label: "",
        schema: { field_type: "text" },
        ui: { placeholder: "" },
      };
    case "rating":
      return {
        family: "rating",
        label: "",
        schema: { min: 1, max: 5 },
        ui: { style: "slider" },
      };
    case "matching":
      return {
        family: "matching",
        label: "",
        schema: {
          left_items:  [{ id: "c1", label: "" }],
          right_items: [{ id: "r1", label: "" }],
        },
        ui: { style: "drag_match" },
      };
  }
}

export function QuestionEditor({ open, onClose, onSave, initial }: QuestionEditorProps) {
  const [key,    setKey]    = useState("");
  const [family, setFamily] = useState<QuestionType>("choice");
  const [schema, setSchema] = useState<Record<string, unknown>>(defaultQuestionSchema("choice"));
  const [saving, setSaving] = useState(false);
  const [error,  setError]  = useState<string | string[] | null>(null);

  useEffect(() => {
    if (!open) return;

    const nextFamily = (initial?.question_schema?.family as QuestionType) ?? "choice";
    setKey(initial?.question_key ?? "");
    setFamily(nextFamily);
    setSchema(initial?.question_schema ?? defaultQuestionSchema(nextFamily));
    setError(null);
    setSaving(false);
  }, [initial, open]);

  function changeFamily(f: QuestionType) {
    setFamily(f);
    setSchema(defaultQuestionSchema(f));
  }

  function setTopField(k: string, v: unknown) {
    setSchema((prev) => ({ ...prev, [k]: v }));
  }
  function setInnerSchema(k: string, v: unknown) {
    setSchema((prev) => ({
      ...prev,
      schema: { ...(prev.schema as Record<string, unknown>), [k]: v },
    }));
  }
  function setUi(k: string, v: unknown) {
    setSchema((prev) => ({
      ...prev,
      ui: { ...(prev.ui as Record<string, unknown>), [k]: v },
    }));
  }

  // Derived sub-objects
  const inner = (schema.schema as Record<string, unknown>) ?? {};
  const ui    = (schema.ui    as Record<string, unknown>) ?? {};

  // ── Choice options ────────────────────────────────────────────────────────
  const options = (inner.options as OptionItem[]) ?? [];
  function setOption(i: number, field: keyof OptionItem, v: string) {
    const next = [...options]; next[i] = { ...next[i], [field]: v };
    setInnerSchema("options", next);
  }
  function addOption() {
    setInnerSchema("options", [...options, { id: `a${options.length + 1}`, label: "" }]);
  }
  function removeOption(i: number) {
    setInnerSchema("options", options.filter((_, idx) => idx !== i));
  }

  // ── Matching items ────────────────────────────────────────────────────────
  const leftItems  = (inner.left_items  as MatchItem[]) ?? [];
  const rightItems = (inner.right_items as MatchItem[]) ?? [];

  function setLeftItem(i: number, field: keyof MatchItem, v: string) {
    const next = [...leftItems]; next[i] = { ...next[i], [field]: v };
    setInnerSchema("left_items", next);
  }
  function addLeftItem() {
    setInnerSchema("left_items", [...leftItems, { id: `c${leftItems.length + 1}`, label: "" }]);
  }
  function removeLeftItem(i: number) {
    setInnerSchema("left_items", leftItems.filter((_, idx) => idx !== i));
  }

  function setRightItem(i: number, field: keyof MatchItem, v: string) {
    const next = [...rightItems]; next[i] = { ...next[i], [field]: v };
    setInnerSchema("right_items", next);
  }
  function addRightItem() {
    setInnerSchema("right_items", [...rightItems, { id: `r${rightItems.length + 1}`, label: "" }]);
  }
  function removeRightItem(i: number) {
    setInnerSchema("right_items", rightItems.filter((_, idx) => idx !== i));
  }

  async function handleSave() {
    if (!key.trim()) { setError("Question key is required."); return; }
    setSaving(true);
    setError(null);
    try {
      await onSave({ question_key: key.trim(), question_schema: schema });
      onClose();
    } catch (err) {
      if (err instanceof ApiRequestError && err.error.errors?.length) {
        setError(err.error.errors.map((e) => friendlyError(e.field ?? "", e.message)));
      } else {
        setError(err instanceof Error ? err.message : "Failed to save question.");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={initial ? "Edit Question" : "Add Question"}
      width={560}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={handleSave} disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </Button>
        </>
      }
    >
      {error && (
        <div className="error-banner">
          {Array.isArray(error)
            ? error.map((msg, i) => <div key={i}>{msg}</div>)
            : error}
        </div>
      )}

      <Input
        label="Question key"
        value={key}
        onChange={(e) => setKey(e.target.value)}
        placeholder="q_favourite_colour"
        hint="Snake_case identifier, unique per version."
        disabled={!!initial}
      />

      <Select
        label="Family"
        options={FAMILY_OPTIONS}
        value={family}
        onChange={(e) => changeFamily(e.target.value as QuestionType)}
      />

      <Input
        label="Label"
        value={(schema.label as string) ?? ""}
        onChange={(e) => setTopField("label", e.target.value)}
        placeholder="What is your favourite colour?"
      />

      {/* ── Choice ── */}
      {family === "choice" && (
        <>
          <div className="qe-section">
            <div className="qe-section-label">Options</div>
            {options.map((opt, i) => (
              <div key={i} className="qe-option-row">
                <Input
                  placeholder={`ID (e.g. a${i + 1})`}
                  value={opt.id}
                  onChange={(e) => setOption(i, "id", e.target.value)}
                />
                <Input
                  placeholder="Label (e.g. Red)"
                  value={opt.label}
                  onChange={(e) => setOption(i, "label", e.target.value)}
                />
                {options.length > 1 && (
                  <Button size="sm" variant="ghost" onClick={() => removeOption(i)}>✕</Button>
                )}
              </div>
            ))}
            <Button size="sm" variant="secondary" onClick={addOption}>+ Add option</Button>
          </div>

          <div className="qe-row">
            <Input
              label="Min selected"
              type="number"
              min={0}
              value={String((inner.min_selected as number) ?? 1)}
              onChange={(e) => setInnerSchema("min_selected", Number(e.target.value))}
            />
            <Input
              label="Max selected"
              type="number"
              min={1}
              value={String((inner.max_selected as number) ?? 1)}
              onChange={(e) => setInnerSchema("max_selected", Number(e.target.value))}
            />
          </div>

          <Select
            label="Display style"
            options={CHOICE_STYLE_OPTIONS}
            value={(ui.style as string) ?? "radio"}
            onChange={(e) => setUi("style", e.target.value)}
          />
        </>
      )}

      {/* ── Field ── */}
      {family === "field" && (
        <>
          <Select
            label="Field type"
            options={FIELD_TYPE_OPTIONS}
            value={(inner.field_type as string) ?? "text"}
            onChange={(e) => setInnerSchema("field_type", e.target.value)}
          />
          <Input
            label="Placeholder"
            value={(ui.placeholder as string) ?? ""}
            onChange={(e) => setUi("placeholder", e.target.value)}
            placeholder="e.g. name@example.com"
          />
        </>
      )}

      {/* ── Rating ── */}
      {family === "rating" && (
        <>
          <div className="qe-row">
            <Input
              label="Min"
              type="number"
              value={String((inner.min as number) ?? 1)}
              onChange={(e) => setInnerSchema("min", Number(e.target.value))}
            />
            <Input
              label="Max"
              type="number"
              min={2}
              max={10}
              value={String((inner.max as number) ?? 5)}
              onChange={(e) => setInnerSchema("max", Number(e.target.value))}
            />
          </div>
          <Select
            label="Display style"
            options={RATING_STYLE_OPTIONS}
            value={(ui.style as string) ?? "slider"}
            onChange={(e) => setUi("style", e.target.value)}
          />
        </>
      )}

      {/* ── Matching ── */}
      {family === "matching" && (
        <>
          <div className="qe-section">
            <div className="qe-section-label">Left items (prompts)</div>
            {leftItems.map((item, i) => (
              <div key={i} className="qe-option-row">
                <Input
                  placeholder={`ID (e.g. c${i + 1})`}
                  value={item.id}
                  onChange={(e) => setLeftItem(i, "id", e.target.value)}
                />
                <Input
                  placeholder="Label (e.g. Australia)"
                  value={item.label}
                  onChange={(e) => setLeftItem(i, "label", e.target.value)}
                />
                {leftItems.length > 1 && (
                  <Button size="sm" variant="ghost" onClick={() => removeLeftItem(i)}>✕</Button>
                )}
              </div>
            ))}
            <Button size="sm" variant="secondary" onClick={addLeftItem}>+ Add left item</Button>
          </div>

          <div className="qe-section">
            <div className="qe-section-label">Right items (answers)</div>
            {rightItems.map((item, i) => (
              <div key={i} className="qe-option-row">
                <Input
                  placeholder={`ID (e.g. r${i + 1})`}
                  value={item.id}
                  onChange={(e) => setRightItem(i, "id", e.target.value)}
                />
                <Input
                  placeholder="Label (e.g. Canberra)"
                  value={item.label}
                  onChange={(e) => setRightItem(i, "label", e.target.value)}
                />
                {rightItems.length > 1 && (
                  <Button size="sm" variant="ghost" onClick={() => removeRightItem(i)}>✕</Button>
                )}
              </div>
            ))}
            <Button size="sm" variant="secondary" onClick={addRightItem}>+ Add right item</Button>
          </div>
        </>
      )}
    </Modal>
  );
}
