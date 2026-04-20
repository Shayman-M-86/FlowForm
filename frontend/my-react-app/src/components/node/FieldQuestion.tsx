import { useEffect, useState, forwardRef, useImperativeHandle } from "react";
import "./FieldQuestion.css";
import { QUESTION_MAX, blurOnEnter } from "./NodePillUtils";
import { NodePillTopbar, NodePillQuestionField, NodePillCharCount, NodePillFieldHead } from "./NodePillShell";
import { Input } from "../ui/Input";
import { LargeInput } from "../ui/LargeInput";
import { Select } from "../ui/Select";
import type { FieldContent, FieldType } from "./questionTypes";

export interface FieldQuestionHandle {
  getData(): FieldContent;
}

interface FieldQuestionProps {
  onDelete?: () => void;
  title?: string;
  onEditModeChange?: (isEditMode: boolean) => void;
  onDataChange?: (content: FieldContent) => void;
}

const FIELD_TYPE_OPTIONS: Array<{ value: FieldType; label: string }> = [
  { value: "short_text", label: "Short text" },
  { value: "long_text", label: "Long text" },
  { value: "email", label: "Email" },
  { value: "phone", label: "Phone" },
  { value: "number", label: "Number" },
  { value: "date", label: "Date" },
];

const FIELD_TYPE_PRESETS: Record<FieldType, { placeholder: string; helper: string }> = {
  "short_text": {
    placeholder: "Type a short response",
    helper: "Single-line text input.",
  },
  "long_text": {
    placeholder: "Type a longer response",
    helper: "Multi-line text area.",
  },
  email: {
    placeholder: "name@example.com",
    helper: "Email-formatted input.",
  },
  phone: {
    placeholder: "(555) 123-4567",
    helper: "Phone number input.",
  },
  number: {
    placeholder: "Enter a number",
    helper: "Numeric-only input.",
  },
  date: {
    placeholder: "",
    helper: "Calendar date input.",
  },
};

export const FieldQuestion = forwardRef<FieldQuestionHandle, FieldQuestionProps>(function FieldQuestion({ onDelete, title, onEditModeChange, onDataChange }, ref) {
  const [isEditMode, setIsEditMode] = useState(true);
  const [titleValue, setTitleValue] = useState(title ?? "");
  const [questionValue, setQuestionValue] = useState("");
  const [tagValue, setTagValue] = useState("question_id_1");
  const [fieldType, setFieldType] = useState<FieldType>("short_text");
  const [placeholderValue, setPlaceholderValue] = useState(
    FIELD_TYPE_PRESETS["short_text"].placeholder,
  );
  const [fieldValue, setFieldValue] = useState("");

  const fieldQuestionData: FieldContent = {
    id: tagValue,
    title: titleValue,
    label: questionValue,
    family: "field",
    definition: {
      field_type: fieldType,
      ui: fieldType === "date"
        ? {}
        : { placeholder: placeholderValue },
    },
  };

  useImperativeHandle(ref, () => ({
    getData() {
      return fieldQuestionData;
    },
  }));

  useEffect(() => {
    onDataChange?.(fieldQuestionData);
  }, [titleValue, tagValue, questionValue, fieldType, placeholderValue]);

  function updateFieldType(nextType: FieldType) {
    setFieldType(nextType);
    setPlaceholderValue(FIELD_TYPE_PRESETS[nextType].placeholder);
    setFieldValue("");
  }

  function toggleEditMode() {
    setIsEditMode((current) => {
      const nextMode = !current;
      onEditModeChange?.(nextMode);
      return nextMode;
    });
  }

  const fieldLabel = FIELD_TYPE_OPTIONS.find((option) => option.value === fieldType)?.label ?? "Field";
  const fieldPreset = FIELD_TYPE_PRESETS[fieldType];
  const isWideField = fieldType === "long_text";
  const fieldMaxLength = fieldType === "short_text" ? 100 : fieldType === "long_text" ? 1000 : undefined;

  return (
    <section className={`node-pill field-question ${isEditMode ? "node-pill--edit" : ""}`} aria-label="Field question">
      <NodePillTopbar
        family="Field"
        tagValue={tagValue}
        onTagChange={setTagValue}
        isEditMode={isEditMode}
        onToggleEditMode={toggleEditMode}
        onDelete={onDelete}
      />

      <div className="node-pill__body">
        <NodePillQuestionField
          value={questionValue}
          onChange={setQuestionValue}
          isEditMode={isEditMode}
          max={QUESTION_MAX}
          titleValue={titleValue}
          onTitleChange={setTitleValue}
          showTitleEdit={true}
        />

        <div className="node-pill__field">
          <NodePillFieldHead label="Field">
            {isEditMode && (
              <NodePillCharCount
                label="Type"
                value={fieldLabel}
              />
            )}
          </NodePillFieldHead>

          <div className="field-question__panel">
            {isEditMode && (
              <>
                <div className="field-question__controls">
                  <Select
                    className="field-question__control"
                    label="Type"
                    value={fieldType}
                    options={FIELD_TYPE_OPTIONS}
                    hint={fieldPreset.helper}
                    onChange={(event) => updateFieldType(event.target.value as FieldType)}
                  />

                  {fieldType !== "date" && (
                    <Input
                      className="field-question__control field-question__control--placeholder"
                      label="Placeholder"
                      type="text"
                      placeholder="Field placeholder"
                      value={placeholderValue}
                      maxLength={50}
                      onChange={(event) => setPlaceholderValue(event.target.value)}
                      onKeyDown={blurOnEnter}
                    />
                  )}
                </div>

              </>
            )}

            <div className="field-question__preview">
              <span className="field-question__preview-title">{fieldLabel}</span>

              {fieldType === "long_text" ? (
                <LargeInput
                  className="field-question__preview-textarea"
                  size="sm"
                  rows={4}
                  autoGrow
                  maxAutoGrowHeight={220}
                  placeholder={placeholderValue}
                  maxText={fieldMaxLength}
                  value={fieldValue}
                  onChange={(event) => setFieldValue(event.target.value)}
                />
              ) : (
                <Input
                  className={`field-question__preview-input-field ${!isWideField ? "field-question__preview-input-field--compact" : ""}`}
                  type={fieldType === "short_text" ? "text" : fieldType}
                  placeholder={placeholderValue}
                  value={fieldValue}
                  maxLength={fieldMaxLength}
                  onChange={(event) => setFieldValue(event.target.value)}
                />
              )}
              {fieldMaxLength !== undefined && fieldValue.length === fieldMaxLength && (
                <span className="node-pill__option-limit">Maximum characters reached.</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
});
