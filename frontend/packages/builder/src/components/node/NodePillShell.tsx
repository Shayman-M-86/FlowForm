import type { ReactNode } from "react";
import { createContext, useContext, useState } from "react";

import { TAG_MAX, blurOnEnter, sanitizeQuestionId } from "./NodePillUtils";

import { Badge, Button, Input, LargeInput, Modal, Tooltip } from "@flowform/ui";
import {
  nodePillCollapsedShellClass,
  nodePillFieldClass,
  nodePillFieldHeadClass,
  nodePillLabelClass,
  nodePillLimitTextClass,
  nodePillTopbarClass,
} from "./nodePillStyles";

type MobileControls = { leading?: ReactNode; trailing?: ReactNode };
const MobileControlsContext = createContext<MobileControls>({});
export const NodePillMobileControlsProvider = MobileControlsContext.Provider;

type TopbarProps = {
  family: string;
  isEditMode: boolean;
  onToggleEditMode: () => void;
  onDelete?: () => void;
  actions?: ReactNode;
  idField?: ReactNode;
};

export function NodePillTopbar({
  family,
  isEditMode,
  onToggleEditMode,
  onDelete,
  actions,
  idField,
}: TopbarProps) {
  const { leading, trailing } = useContext(MobileControlsContext);
  return (
    <header className={nodePillTopbarClass}>
      <div className="flex min-w-0 grow items-center gap-3">
        {leading && (
          <span className="hidden max-[640px]:flex items-center">{leading}</span>
        )}
        <Badge variant="accent" size="md">{family}</Badge>
        {idField}
      </div>
      <div className="ml-auto flex shrink-0 items-center gap-3">
        {isEditMode && (actions ?? (
          <>
            <Button
              className="whitespace-nowrap"
              type="button"
              variant="danger"
              size="xs"
              pill
              onClick={onDelete}
            >
              Delete
            </Button>
            <Button className="whitespace-nowrap" type="button" variant="secondary" size="xs" pill>
              Settings
            </Button>
          </>
        ))}
        <Button
          className="whitespace-nowrap"
          type="button"
          variant="secondary"
          size="xs"
          pill
          onClick={onToggleEditMode}
        >
          {isEditMode ? "Editing" : "Edit"}
        </Button>
        {trailing && (
          <span className="hidden max-[640px]:flex items-center gap-2">{trailing}</span>
        )}
      </div>
    </header>
  );
}

type IdFieldProps = {
  tagValue: string;
  onTagChange: (next: string) => void;
  idError?: string;
  isEditMode: boolean;
};

export function NodePillIdField({ tagValue, onTagChange, idError, isEditMode }: IdFieldProps) {
  return (
    <div className="ml-auto flex flex-col items-end gap-1">
      <div className="flex items-center gap-1 rounded-full border border-border bg-card/60 shadow-xs">
        <Tooltip
          title="Identifier for this question. Lowercase only; no spaces or capitals."
          size="sm"
        >
          <h6 className="pl-2 text-muted-foreground">ID</h6>
        </Tooltip>
        <Input
          type="text"
          className="border-l border-border rounded-xl"
          placeholder={isEditMode ? "question_id" : ""}
          value={tagValue}
          size="xs"
          maxLength={TAG_MAX}
          readOnly={!isEditMode}
          variant="ghost"
          pill
          onChange={(event) => onTagChange(sanitizeQuestionId(event.target.value))}
          onKeyDown={blurOnEnter}
        />
      </div>
      {idError && (
        <span className="text-[0.78rem] text-destructive">{idError}</span>
      )}
    </div>
  );
}

type TitleFieldProps = {
  value: string;
  onChange: (next: string) => void;
  isEditMode: boolean;
  max?: number;
};

export function NodePillTitleField({
  value,
  onChange,
  isEditMode,
  max = 80,
}: TitleFieldProps) {
  return (
    <div className={nodePillFieldClass}>
      <div className="flex flex-col gap-2 w-4/5">
        <Input
          type="text"
          placeholder="Enter a title (optional)"
          maxLength={max}
          value={value}
          readOnly={!isEditMode}
          variant={isEditMode ? "secondary" : "ghost"}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={blurOnEnter}
        />
        {isEditMode && value.length === max && (
          <span className={`${nodePillLimitTextClass} px-1.5`}>
            Maximum {max} characters reached.
          </span>
        )}
      </div>
    </div>
  );
}

type QuestionFieldProps = {
  value: string;
  onChange: (next: string) => void;
  isEditMode: boolean;
  max: number;
};

type QuestionFieldWithTitleProps = QuestionFieldProps & {
  titleValue?: string;
  onTitleChange?: (next: string) => void;
  titleMax?: number;
  showTitleEdit?: boolean;
};

export function NodePillQuestionField({
  value,
  onChange,
  isEditMode,
  max,
  titleValue,
  onTitleChange,
  titleMax = 80,
  showTitleEdit = false,
}: QuestionFieldWithTitleProps) {
  const [isTitleEditMode, setIsTitleEditMode] = useState(false);
  const hasTitle = titleValue !== undefined && onTitleChange !== undefined;

  const handleTitleClick = () => {
    if (isEditMode && hasTitle && showTitleEdit) {
      setIsTitleEditMode(true);
    }
  };

  const handleTitleSubmit = () => {
    setIsTitleEditMode(false);
  };

  return (
    <div className={nodePillFieldClass}>
      <div className="mb-2 flex items-center gap-1.5">
        <span className={nodePillLabelClass}>
          {hasTitle && titleValue ? titleValue : "Question"}
        </span>
        {hasTitle && showTitleEdit && isEditMode && (
          <Button
            className="mt-1 !p-1"
            type="button"
            variant="ghost"
            size="xxs"
            onClick={handleTitleClick}
            aria-label="Edit title"
          >
            ✎
          </Button>
        )}
      </div>
      {hasTitle && (
        <Modal
          open={isTitleEditMode}
          onClose={() => setIsTitleEditMode(false)}
          title="Edit title"
          width={420}
          footer={(
            <>
              <Button type="button" variant="secondary" onClick={() => setIsTitleEditMode(false)}>
                Cancel
              </Button>
              <Button type="button" variant="primary" onClick={handleTitleSubmit}>
                Save
              </Button>
            </>
          )}
        >
          <Input
            label="Title"
            type="text"
            placeholder="Enter a title (optional)"
            maxLength={titleMax}
            value={titleValue}
            onChange={(event) => onTitleChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") handleTitleSubmit();
              if (event.key === "Escape") setIsTitleEditMode(false);
            }}
            autoFocus
          />
        </Modal>
      )}
      <div className="flex flex-col gap-2">
        <LargeInput
          className="w-full"
          placeholder="Type your question here"
          rows={3}
          size="sm"
          autoGrow
          maxAutoGrowHeight={640}
          maxText={max}
          value={value}
          readOnly={!isEditMode}
          variant={isEditMode ? "secondary" : "ghost"}
          onChange={(event) => onChange(event.target.value)}
        />
        {isEditMode && value.length === max && (
          <span className={nodePillLimitTextClass}>
            Maximum {max} characters reached.
          </span>
        )}
      </div>
    </div>
  );
}

type CharCountProps = {
  label: string;
  value: number | string;
  max?: number | string;
  tooltip?: string;
};

export function NodePillCharCount({ label, value, max, tooltip }: CharCountProps) {
  const labelClass = "cursor-default text-muted-foreground";
  const labelNode = tooltip ? (
    <Tooltip title={tooltip} size="sm">
      <span className={labelClass}>{label}</span>
    </Tooltip>
  ) : (
    <span className={labelClass}>{label}</span>
  );

  return (
    <span className="ml-1 flex items-center gap-1 text-[0.72rem] text-muted-foreground">
      <span className="flex items-center gap-0.5">
        {labelNode}
        <span className="tabular-nums">{value}</span>
      </span>
      {max !== undefined && (
        <>
          <span className="text-muted-foreground">/</span>
          <span className="flex items-center gap-0.5">
            <span className={labelClass}>Max</span>
            <span className="tabular-nums">{max}</span>
          </span>
        </>
      )}
    </span>
  );
}

type FieldHeadProps = {
  label: string;
  children?: ReactNode;
};

export function NodePillFieldHead({ label, children }: FieldHeadProps) {
  return (
    <span className={nodePillFieldHeadClass}>
      <span className={nodePillLabelClass}>{label}</span>
      {children}
    </span>
  );
}

type DragLocks = {
  reverseLock?: { siblingId: string; direction: "down" | "up" } | null;
  insertLock?: { siblingId: string; direction: "down" | "up" } | null;
};

type DragThresholdsProps = {
  itemId: string;
  isDragging: boolean;
  thresholdRatio: number | null;
  activeDrag: DragLocks | null;
};

export function NodePillDragThresholds({
  itemId,
  isDragging,
  thresholdRatio,
  activeDrag,
}: DragThresholdsProps) {
  void itemId;
  void isDragging;
  void thresholdRatio;
  void activeDrag;
  return null;
}

type CollapsedProps = {
  family: string;
  tagValue: string;
  title: string;
  onExpand: () => void;
};

export function NodePillCollapsed({ family, tagValue, title, onExpand }: CollapsedProps) {
  const { leading } = useContext(MobileControlsContext);
  return (
    <div className={nodePillCollapsedShellClass}>
      <div className="flex items-center gap-3 px-3.5 py-3.5">
        {leading && (
          <span className="hidden max-[640px]:flex items-center">{leading}</span>
        )}
        <Badge variant="accent" size="md">{family}</Badge>
        <div className="flex flex-1 min-w-0 items-baseline gap-2.5 overflow-hidden">
          <span className="overflow-hidden text-ellipsis whitespace-nowrap text-[0.88rem] font-semibold text-foreground">
            {title.trim() || "Untitled question"}
          </span>
          <span className="shrink-0 overflow-hidden text-ellipsis whitespace-nowrap text-[0.78rem] text-muted-foreground">
            {tagValue}
          </span>
        </div>
        <Button
          type="button"
          variant="secondary"
          size="xs"
          pill
          onClick={onExpand}
        >
          Edit
        </Button>
      </div>
    </div>
  );
}

export { nodePillShellClass, nodePillShellEditClass, nodePillBodyClass, nodePillFieldClass } from "./nodePillStyles";
