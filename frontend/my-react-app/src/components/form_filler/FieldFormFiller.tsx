import type { HTMLInputTypeAttribute } from "react";
import { Input } from "../ui/Input";
import { LargeInput } from "../ui/LargeInput";
import type { FieldContent } from "../node/questionTypes";
import "../node/FieldQuestion.css";

interface FieldFormFillerProps {
  question: FieldContent;
  value: string;
  onChange: (nextValue: string) => void;
}

export function FieldFormFiller({
  question,
  value,
  onChange,
}: FieldFormFillerProps) {
  const placeholder = question.definition.ui.placeholder ?? "Enter your response";
  const fieldMeta = getFieldMeta(question.definition.field_type);
  const fieldMaxLength = question.definition.field_type === "short_text"
    ? 100
    : question.definition.field_type === "long_text"
      ? 1000
      : undefined;

  return (
    <div className="form-filler-question__body">
      <div className="field-question__preview">
        <span className="field-question__preview-title">{fieldMeta.label}</span>

        {question.definition.field_type === "long_text" ? (
          <LargeInput
            className="field-question__preview-textarea"
            size="sm"
            rows={4}
            autoGrow
            maxAutoGrowHeight={220}
            placeholder={placeholder}
            maxText={fieldMaxLength}
            value={value}
            onChange={(event) => onChange(event.target.value)}
          />
        ) : (
          <Input
            className="field-question__preview-input-field field-question__preview-input-field--compact"
            type={mapInputType(question.definition.field_type)}
            placeholder={placeholder}
            value={value}
            maxLength={fieldMaxLength}
            onChange={(event) => onChange(event.target.value)}
          />
        )}
      </div>
      <p className="form-filler-question__helper">{fieldMeta.helper}</p>
    </div>
  );
}

function mapInputType(fieldType: FieldContent["definition"]["field_type"]): HTMLInputTypeAttribute {
  switch (fieldType) {
    case "email":
      return "email";
    case "phone":
      return "tel";
    case "number":
      return "number";
    case "date":
      return "date";
    default:
      return "text";
  }
}

function getFieldMeta(fieldType: FieldContent["definition"]["field_type"]) {
  switch (fieldType) {
    case "short_text":
      return { label: "Short text", helper: "Single-line text input." };
    case "long_text":
      return { label: "Long text", helper: "Multi-line text area." };
    case "email":
      return { label: "Email", helper: "Email-formatted input." };
    case "phone":
      return { label: "Phone", helper: "Phone number input." };
    case "number":
      return { label: "Number", helper: "Numeric-only input." };
    case "date":
      return { label: "Date", helper: "Calendar date input." };
    default:
      return { label: "Field", helper: "Enter your response." };
  }
}
