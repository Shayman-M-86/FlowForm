import type { HTMLInputTypeAttribute } from "react";
import { Input, LargeInput } from "@flowform/ui";
import type { FieldContent } from "../node/questionTypes";

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
    <div className="flex flex-col gap-4.5">
      <div className="flex flex-col gap-3 rounded-2xl border border-border bg-muted/20 p-4">
        <span className="text-[0.78rem] font-semibold uppercase tracking-[0.04em] text-muted-foreground">
          {fieldMeta.label}
        </span>

        {question.definition.field_type === "long_text" ? (
          <LargeInput
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
            className="w-full max-w-112.5"
            type={mapInputType(question.definition.field_type)}
            placeholder={placeholder}
            value={value}
            maxLength={fieldMaxLength}
            onChange={(event) => onChange(event.target.value)}
          />
        )}
      </div>
      <p className="m-0 text-[0.92rem] text-muted-foreground">{fieldMeta.helper}</p>
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
