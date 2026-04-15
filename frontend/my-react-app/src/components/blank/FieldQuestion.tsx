import { useState, forwardRef, useImperativeHandle } from "react";
import "./FieldQuestion.css";
import { QUESTION_MAX, autoResizeTextarea, blurOnEnter } from "./blankPillUtils";
import { BlankPillTopbar, BlankPillQuestionField, BlankPillCharCount, BlankPillFieldHead } from "./BlankPillShell";

export type { FieldQuestionData };

export interface FieldQuestionHandle {
  getData(): FieldQuestionData;
}

interface FieldQuestionProps {
  onDelete?: () => void;
  title?: string;
}

type FieldType = "short_text" | "long_text" | "email" | "phone" | "number" | "date";

interface FieldQuestionData {
  id: string;
  title: string;
  label: string;
  family: "field";
  field: {
    schema: {
      field_type: FieldType;
    };
    ui: {
      placeholder: string;
    };
  };
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

export const FieldQuestion = forwardRef<FieldQuestionHandle, FieldQuestionProps>(function FieldQuestion({ onDelete, title }, ref) {
  const [isEditMode, setIsEditMode] = useState(true);
  const [titleValue, setTitleValue] = useState(title ?? "");
  const [questionValue, setQuestionValue] = useState("");
  const [tagValue, setTagValue] = useState("question_id_1");
  const [fieldType, setFieldType] = useState<FieldType>("short_text");
  const [placeholderValue, setPlaceholderValue] = useState(
    FIELD_TYPE_PRESETS["short_text"].placeholder,
  );
  const [fieldValue, setFieldValue] = useState("");

  const fieldQuestionData: FieldQuestionData = {
    id: tagValue,
    title: titleValue,
    label: questionValue,
    family: "field",
    field: {
      schema: {
        field_type: fieldType,
      },
      ui: {
        placeholder: placeholderValue,
      },
    },
  };

  useImperativeHandle(ref, () => ({
    getData() {
      return fieldQuestionData;
    },
  }));

  function updateFieldType(nextType: FieldType) {
    setFieldType(nextType);
    setPlaceholderValue(FIELD_TYPE_PRESETS[nextType].placeholder);
    setFieldValue("");
  }

  const fieldLabel = FIELD_TYPE_OPTIONS.find((option) => option.value === fieldType)?.label ?? "Field";
  const fieldPreset = FIELD_TYPE_PRESETS[fieldType];
  const isWideField = fieldType === "long_text";
  const fieldMaxLength = fieldType === "short_text" ? 100 : fieldType === "long_text" ? 1000 : undefined;

  return (
    <section className={`blank-pill field-question ${isEditMode ? "blank-pill--edit" : ""}`} aria-label="Field question">
      <BlankPillTopbar
        family="Field"
        tagValue={tagValue}
        onTagChange={setTagValue}
        isEditMode={isEditMode}
        onToggleEditMode={() => setIsEditMode((mode) => !mode)}
        onDelete={onDelete}
      />

      <div className="blank-pill__body">
        <BlankPillQuestionField
          value={questionValue}
          onChange={setQuestionValue}
          isEditMode={isEditMode}
          max={QUESTION_MAX}
          titleValue={titleValue}
          onTitleChange={setTitleValue}
          showTitleEdit={true}
        />

        <div className="blank-pill__field">
          <BlankPillFieldHead label="Field">
            {isEditMode && (
              <BlankPillCharCount
                label="Type"
                value={fieldLabel}
              />
            )}
          </BlankPillFieldHead>

          <div className="field-question__panel">
            {isEditMode && (
              <>
                <div className="field-question__controls">
                  <label className="field-question__control">
                    <span className="field-question__control-label">Type</span>
                    <select
                      className="field-question__select"
                      value={fieldType}
                      onChange={(event) => updateFieldType(event.target.value as FieldType)}
                    >
                      {FIELD_TYPE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>

                  {fieldType !== "date" && (
                    <label className="field-question__control field-question__control--wide field-question__control--placeholder">
                      <span className="field-question__control-label">Placeholder</span>
                      <input
                        className="field-question__text-input"
                        type="text"
                        placeholder="Field placeholder"
                        value={placeholderValue}
                        maxLength={50}
                        onChange={(event) => setPlaceholderValue(event.target.value)}
                        onKeyDown={blurOnEnter}
                      />
                    </label>
                  )}
                </div>

                <div className="field-question__helper">{fieldPreset.helper}</div>
              </>
            )}

            <div className="field-question__preview">
              <div className="field-question__preview-head">
                <span className="field-question__preview-title">{fieldLabel}</span>
              </div>

              {fieldType === "long_text" ? (
                <div className="field-question__textarea-shell">
                  <textarea
                    className={`field-question__input field-question__input--textarea ${!isWideField ? "field-question__input--compact" : ""}`}
                    rows={4}
                    placeholder={placeholderValue}
                    maxLength={fieldMaxLength}
                    value={fieldValue}
                    onChange={(event) => setFieldValue(event.target.value)}
                    onInput={(event) => autoResizeTextarea(event.currentTarget)}
                  />
                </div>
              ) : (
                <input
                  className={`field-question__input ${!isWideField ? "field-question__input--compact" : ""}`}
                  type={fieldType === "short_text" ? "text" : fieldType}
                  placeholder={placeholderValue}
                  value={fieldValue}
                  maxLength={fieldMaxLength}
                  onChange={(event) => setFieldValue(event.target.value)}
                />
              )}
              {fieldMaxLength !== undefined && fieldValue.length === fieldMaxLength && (
                <span className="blank-pill__option-limit">Maximum characters reached.</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
});
