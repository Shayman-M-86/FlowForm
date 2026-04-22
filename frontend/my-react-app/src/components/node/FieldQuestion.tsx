import { useEffect, useState, forwardRef, useImperativeHandle } from "react";
import { QUESTION_MAX, blurOnEnter } from "./NodePillUtils";
import {
  NodePillTopbar,
  NodePillQuestionField,
  NodePillCharCount,
  NodePillFieldHead,
  NodePillCollapsed,
} from "./NodePillShell";
import {
  nodePillBodyClass,
  nodePillFieldClass,
  nodePillLimitTextClass,
  nodePillPanelClass,
  nodePillPreviewClass,
  nodePillShellClass,
  nodePillShellEditClass,
  nodePillSubLabelClass,
} from "./nodePillStyles";
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
  initialTag?: string;
  initialContent?: FieldContent;
  idError?: string;
  isCollapsed?: boolean;
  onExpand?: () => void;
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
  "short_text": { placeholder: "Type a short response", helper: "Single-line text input." },
  "long_text": { placeholder: "Type a longer response", helper: "Multi-line text area." },
  email: { placeholder: "name@example.com", helper: "Email-formatted input." },
  phone: { placeholder: "(555) 123-4567", helper: "Phone number input." },
  number: { placeholder: "Enter a number", helper: "Numeric-only input." },
  date: { placeholder: "", helper: "Calendar date input." },
};

export const FieldQuestion = forwardRef<FieldQuestionHandle, FieldQuestionProps>(function FieldQuestion({ onDelete, title, initialTag, initialContent, idError, isCollapsed, onExpand, onEditModeChange, onDataChange }, ref) {
  const [isEditMode, setIsEditMode] = useState(true);
  const initialFieldType = initialContent?.definition.field_type ?? "short_text";
  const [titleValue, setTitleValue] = useState(initialContent?.title ?? title ?? "");
  const [questionValue, setQuestionValue] = useState(initialContent?.label ?? "");
  const [tagValue, setTagValue] = useState(initialContent?.id ?? initialTag ?? "question_id_1");
  const [fieldType, setFieldType] = useState<FieldType>(initialFieldType);
  const [placeholderValue, setPlaceholderValue] = useState(
    initialContent?.definition.ui.placeholder ?? FIELD_TYPE_PRESETS[initialFieldType].placeholder,
  );
  const [fieldValue, setFieldValue] = useState("");

  const fieldQuestionData: FieldContent = {
    id: tagValue,
    title: titleValue,
    label: questionValue,
    family: "field",
    definition: {
      field_type: fieldType,
      ui: fieldType === "date" ? {} : { placeholder: placeholderValue },
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

  if (isCollapsed) {
    return <NodePillCollapsed family="Field" tagValue={tagValue} title={titleValue} onExpand={() => { onExpand?.(); setIsEditMode(true); onEditModeChange?.(true); }} />;
  }

  return (
    <section className={`${nodePillShellClass} ${isEditMode ? nodePillShellEditClass : ""}`} aria-label="Field question">
      <NodePillTopbar
        family="Field"
        tagValue={tagValue}
        onTagChange={setTagValue}
        idError={idError}
        isEditMode={isEditMode}
        onToggleEditMode={toggleEditMode}
        onDelete={onDelete}
      />

      <div className={nodePillBodyClass}>
        <NodePillQuestionField
          value={questionValue}
          onChange={setQuestionValue}
          isEditMode={isEditMode}
          max={QUESTION_MAX}
          titleValue={titleValue}
          onTitleChange={setTitleValue}
          showTitleEdit={true}
        />

        <div className={nodePillFieldClass}>
          <NodePillFieldHead label="Field">
            {isEditMode && <NodePillCharCount label="Type" value={fieldLabel} />}
          </NodePillFieldHead>

          <div className={nodePillPanelClass}>
            {isEditMode && (
              <div className="grid gap-4 md:grid-cols-[240px_minmax(0,1fr)]">
                <Select
                  className="min-w-0"
                  label="Type"
                  value={fieldType}
                  options={FIELD_TYPE_OPTIONS}
                  hint={fieldPreset.helper}
                  onChange={(event) => updateFieldType(event.target.value as FieldType)}
                />

                {fieldType !== "date" && (
                  <Input
                    className="min-w-0 max-w-110"
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
            )}

            <div className={nodePillPreviewClass}>
              <span className={nodePillSubLabelClass}>{fieldLabel}</span>

              {fieldType === "long_text" ? (
                <LargeInput
                  className="w-full"
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
                  className={`${isWideField ? "w-full" : "w-full max-w-112.5"}`}
                  type={fieldType === "short_text" ? "text" : fieldType}
                  placeholder={placeholderValue}
                  value={fieldValue}
                  maxLength={fieldMaxLength}
                  onChange={(event) => setFieldValue(event.target.value)}
                />
              )}
              {fieldMaxLength !== undefined && fieldValue.length === fieldMaxLength && (
                <span className={`${nodePillLimitTextClass} px-1.5`}>Maximum characters reached.</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
});
