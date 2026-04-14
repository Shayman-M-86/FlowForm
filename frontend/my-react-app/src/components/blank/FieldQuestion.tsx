import { useState } from "react";
import "./FieldQuestion.css";

const QUESTION_MAX = 5000;

type FieldType = "short-text" | "long-text" | "email" | "phone" | "number" | "date";

const FIELD_TYPE_OPTIONS: Array<{ value: FieldType; label: string }> = [
  { value: "short-text", label: "Short text" },
  { value: "long-text", label: "Long text" },
  { value: "email", label: "Email" },
  { value: "phone", label: "Phone" },
  { value: "number", label: "Number" },
  { value: "date", label: "Date" },
];

const FIELD_TYPE_PRESETS: Record<FieldType, { placeholder: string; helper: string }> = {
  "short-text": {
    placeholder: "Type a short response",
    helper: "Single-line text input.",
  },
  "long-text": {
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

export function FieldQuestion() {
  const [isEditMode, setIsEditMode] = useState(true);
  const [questionValue, setQuestionValue] = useState("");
  const [tagValue, setTagValue] = useState("question_id_1");
  const [fieldType, setFieldType] = useState<FieldType>("short-text");
  const [placeholderValue, setPlaceholderValue] = useState(
    FIELD_TYPE_PRESETS["short-text"].placeholder,
  );
  const [fieldValue, setFieldValue] = useState("");

  function blurOnEnter(event: React.KeyboardEvent<HTMLElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      (event.currentTarget as HTMLElement).blur();
    }
  }

  function autoResizeTextarea(element: HTMLTextAreaElement) {
    element.style.height = "0px";
    const maxHeight = element.classList.contains("blank-pill__question") ? 600 : 220;
    const nextHeight = Math.min(element.scrollHeight, maxHeight);
    element.style.height = `${nextHeight}px`;
    element.style.overflowY = element.scrollHeight > maxHeight ? "auto" : "hidden";
  }

  function updateFieldType(nextType: FieldType) {
    setFieldType(nextType);
    setPlaceholderValue(FIELD_TYPE_PRESETS[nextType].placeholder);
    setFieldValue("");
  }

  const fieldLabel = FIELD_TYPE_OPTIONS.find((option) => option.value === fieldType)?.label ?? "Field";
  const fieldPreset = FIELD_TYPE_PRESETS[fieldType];
  const isWideField = fieldType === "long-text";
  const fieldMaxLength = fieldType === "short-text" ? 100 : fieldType === "long-text" ? 1000 : undefined;

  return (
    <section className={`blank-pill field-question ${isEditMode ? "blank-pill--edit" : ""}`} aria-label="Field question">
      <header className="blank-pill__topbar">
        <div className="blank-pill__topbar-left">
          <span className="blank-pill__family">Field</span>
          <input
            className={`blank-pill__topbar-tag ${!isEditMode ? "blank-pill__topbar-tag--view" : ""}`}
            type="text"
            placeholder={isEditMode ? "question_id" : ""}
            value={tagValue}
            maxLength={40}
            size={Math.max(11, tagValue.length + 2)}
            readOnly={!isEditMode}
            onChange={(event) => setTagValue(event.target.value)}
            onKeyDown={blurOnEnter}
          />
        </div>

        <div className="blank-pill__actions">
          {isEditMode && (
            <>
              <button className="blank-pill__action blank-pill__action--danger" type="button">
                Delete
              </button>
              <button className="blank-pill__action" type="button">
                Settings
              </button>
            </>
          )}
          <button
            className={`blank-pill__action ${isEditMode ? "blank-pill__action--active" : ""}`}
            type="button"
            onClick={() => setIsEditMode((mode) => !mode)}
          >
            {isEditMode ? "Editing" : "Edit"}
          </button>
        </div>
      </header>

      <div className="blank-pill__body">
        <div className="blank-pill__field">
          <span className="blank-pill__label">Question</span>
          <div className="blank-pill__question-stack">
            <div className="blank-pill__question-field">
              <textarea
                className="blank-pill__question"
                placeholder="Type your question here"
                rows={3}
                maxLength={QUESTION_MAX}
                value={questionValue}
                readOnly={!isEditMode}
                onChange={(event) => setQuestionValue(event.target.value)}
                onInput={(event) => autoResizeTextarea(event.currentTarget)}
              />
            </div>
            {isEditMode && questionValue.length === QUESTION_MAX && (
              <span className="blank-pill__question-limit">
                Maximum {QUESTION_MAX} characters reached.
              </span>
            )}
          </div>
        </div>

        <div className="blank-pill__field">
          <span className="blank-pill__field-head">
            <span className="blank-pill__label">Field</span>
            {isEditMode && (
              <span className="blank-pill__answer-char-count">
                <span className="blank-pill__answer-char-count-item">
                  <span className="blank-pill__answer-char-count-label">Type</span>
                  <span className="blank-pill__answer-char-count-value">{fieldLabel}</span>
                </span>
              </span>
            )}
          </span>

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

              {fieldType === "long-text" ? (
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
                  type={fieldType === "short-text" ? "text" : fieldType}
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
}
