import { useState } from "react";
import { QUESTION_MAX, TITLE_MAX, blurOnEnter } from "../NodePillUtils";
import {
  NodePillTopbar,
  NodePillIdField,
  NodePillQuestionField,
  NodePillCharCount,
  NodePillFieldHead,
  NodePillCollapsed,
} from "../NodePillShell";
import {
  nodePillBodyClass,
  nodePillFieldClass,
  nodePillLimitTextClass,
  nodePillPanelClass,
  nodePillPreviewClass,
  nodePillShellClass,
  nodePillShellEditClass,
  nodePillSubLabelClass,
} from "../nodePillStyles";
import { Input, LargeInput, Select } from "@flowform/ui";
import type { FieldContent, FieldType } from "../questionTypes";
import type { CreateQuestionNodeRequest } from "@flowform/schema";

export type FieldQuestionNode = Omit<CreateQuestionNodeRequest, "content"> & {
  content: FieldContent;
};

interface FieldQuestionProps {
  node: FieldQuestionNode;
  onChange: (next: FieldQuestionNode) => void;
  onDelete?: () => void;
  idError?: string;
  validationError?: string;
  isCollapsed?: boolean;
  isEditMode?: boolean;
  onExpand?: () => void;
  onExpandInEditMode?: () => void;
  onEditModeChange?: (isEditMode: boolean) => void;
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
  short_text: { placeholder: "Type a short response", helper: "Single-line text input." },
  long_text: { placeholder: "Type a longer response", helper: "Multi-line text area." },
  email: { placeholder: "name@example.com", helper: "Email-formatted input." },
  phone: { placeholder: "(555) 123-4567", helper: "Phone number input." },
  number: { placeholder: "Enter a number", helper: "Numeric-only input." },
  date: { placeholder: "", helper: "Calendar date input." },
};

export function FieldQuestion({
  node,
  onChange,
  onDelete,
  idError,
  validationError,
  isCollapsed,
  isEditMode = false,
  onExpand,
  onExpandInEditMode,
  onEditModeChange,
}: FieldQuestionProps) {
  const [fieldValue, setFieldValue] = useState("");

  const { content } = node;
  const titleValue = content.title ?? "";
  const questionValue = content.label;
  const fieldType = content.definition.field_type;
  const placeholderValue =
    content.definition.ui?.placeholder ?? FIELD_TYPE_PRESETS[fieldType].placeholder;

  function updateContent(update: (current: FieldContent) => FieldContent) {
    onChange({ ...node, content: update(content) });
  }

  function updateNodeKey(nextNodeKey: string) {
    onChange({ ...node, node_key: nextNodeKey });
  }

  function updateTitle(nextTitle: string) {
    updateContent((current) => ({ ...current, title: nextTitle || undefined }));
  }

  function updateQuestion(nextQuestion: string) {
    updateContent((current) => ({ ...current, label: nextQuestion }));
  }

  function updatePlaceholder(nextPlaceholder: string) {
    updateContent((current) => ({
      ...current,
      definition: {
        ...current.definition,
        ui: { ...current.definition.ui, placeholder: nextPlaceholder },
      },
    }));
  }

  function updateFieldType(nextType: FieldType) {
    const preset = FIELD_TYPE_PRESETS[nextType];
    updateContent((current) => ({
      ...current,
      definition:
        nextType === "date"
          ? { field_type: nextType }
          : { field_type: nextType, ui: { placeholder: preset.placeholder } },
    }));
    setFieldValue("");
  }

  function toggleEditMode() {
    onEditModeChange?.(!isEditMode);
  }

  const fieldLabel =
    FIELD_TYPE_OPTIONS.find((option) => option.value === fieldType)?.label ?? "Field";
  const fieldPreset = FIELD_TYPE_PRESETS[fieldType];
  const fieldMaxLength =
    fieldType === "short_text" ? 100 : fieldType === "long_text" ? 1000 : undefined;
  const previewInputType =
    fieldType === "short_text" ? "text" : fieldType === "phone" ? "tel" : fieldType;

  if (isCollapsed) {
    return (
      <NodePillCollapsed
        family="Field"
        tagValue={node.node_key}
        title={titleValue}
        onExpand={() => onExpand?.()}
        onExpandInEditMode={() => onExpandInEditMode?.()}
      />
    );
  }

  return (
    <section
      className={`${nodePillShellClass} ${isEditMode ? nodePillShellEditClass : ""}`}
      aria-label="Field question"
    >
      <NodePillTopbar
        family="Field"
        isEditMode={isEditMode}
        onToggleEditMode={toggleEditMode}
        onDelete={onDelete}
        settings={{
          tagValue: node.node_key,
          onTagChange: updateNodeKey,
          titleValue,
          onTitleChange: updateTitle,
          idError,
        }}
      />

      <div className={nodePillBodyClass}>
        <NodePillQuestionField
          idField={
            <NodePillIdField
              tagValue={node.node_key}
              onTagChange={updateNodeKey}
              idError={idError}
              isEditMode={isEditMode}
            />
          }
          value={questionValue}
          onChange={updateQuestion}
          isEditMode={isEditMode}
          max={QUESTION_MAX}
          titleValue={titleValue}
          onTitleChange={updateTitle}
          titleMax={TITLE_MAX}
          showTitleEdit
          validationError={validationError}
        />

        <div className={nodePillFieldClass}>
          {isEditMode && (
            <NodePillFieldHead label="Field">
              <NodePillCharCount label="Type" value={fieldLabel} />
            </NodePillFieldHead>
          )}

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
                    onChange={(event) => updatePlaceholder(event.target.value)}
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
                  className="w-full max-w-112.5"
                  type={previewInputType}
                  placeholder={placeholderValue}
                  value={fieldValue}
                  maxLength={fieldMaxLength}
                  onChange={(event) => setFieldValue(event.target.value)}
                />
              )}
              {fieldMaxLength !== undefined && fieldValue.length === fieldMaxLength && (
                <span className={`${nodePillLimitTextClass} px-1.5`}>
                  Maximum characters reached.
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
