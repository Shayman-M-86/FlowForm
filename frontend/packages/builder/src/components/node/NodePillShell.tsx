import type { ReactNode } from "react";
import { createContext, useContext, useRef, useState } from "react";

import { TAG_MAX, blurOnEnter, sanitizeQuestionId } from "./NodePillUtils";

import { Badge, Button, DropdownMenu, Input, LargeInput, Modal, Toggle, Tooltip } from "@flowform/ui";
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
  settings?: NodePillSettings;
};

type NodePillSettings = {
  tagValue: string;
  onTagChange: (next: string) => void;
  titleValue: string;
  onTitleChange: (next: string) => void;
  required?: boolean;
  onRequiredChange?: (next: boolean) => void;
  idError?: string;
};

export function NodePillTopbar({
  family,
  isEditMode,
  onToggleEditMode,
  onDelete,
  actions,
  idField,
  settings,
}: TopbarProps) {
  const { leading, trailing } = useContext(MobileControlsContext);
  const mobileActionsTriggerRef = useRef<HTMLSpanElement>(null);
  const [isMobileActionsOpen, setIsMobileActionsOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const openSettings = settings ? () => setIsSettingsOpen(true) : undefined;
  const defaultActions = (
    <>
      <Button
        className="whitespace-nowrap"
        type="button"
        variant="danger"
        size="xs"
        onClick={onDelete}
      >
        Delete
      </Button>
      {settings && (
        <Button
          className="whitespace-nowrap"
          type="button"
          variant="secondary"
          size="xs"
          onClick={openSettings}
        >
          Settings
        </Button>
      )}
    </>
  );

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
        {isEditMode && (
          actions ?? (
            <>
              <span className="contents max-[640px]:hidden">
                {defaultActions}
              </span>
              <span ref={mobileActionsTriggerRef} className="hidden max-[640px]:inline-flex">
                <Button
                  className="whitespace-nowrap"
                  type="button"
                  variant="secondary"
                  size="xs"
                  aria-haspopup="menu"
                  aria-expanded={isMobileActionsOpen}
                  onClick={() => setIsMobileActionsOpen((open) => !open)}
                >
                  More
                </Button>
              </span>
              <DropdownMenu
                open={isMobileActionsOpen}
                onClose={() => setIsMobileActionsOpen(false)}
                trigger={mobileActionsTriggerRef}
                positioning="absolute"
                size="sm"
                fullscreenAt="never"
                sections={[
                  {
                    actions: [
                      ...(settings ? [{
                        key: "settings",
                        content: "Settings",
                        onSelect: openSettings,
                      }] : []),
                      {
                        key: "delete",
                        content: "Delete",
                        variant: "danger",
                        onSelect: onDelete,
                      },
                    ],
                  },
                ]}
              />
            </>
          )
        )}
        <Button
          className="whitespace-nowrap"
          type="button"
          variant={isEditMode ? "primary" : "secondary"}
          size="xs"
          onClick={onToggleEditMode}
        >
          {isEditMode ? "Editing" : "Edit"}
        </Button>
        {trailing && (
          <span className="hidden max-[640px]:flex items-center gap-2">{trailing}</span>
        )}
      </div>
      {settings && (
        <Modal
          open={isSettingsOpen}
          onClose={() => setIsSettingsOpen(false)}
          title="Question settings"
          width={460}
          footer={(
            <Button type="button" variant="primary" onClick={() => setIsSettingsOpen(false)}>
              Done
            </Button>
          )}
        >
          <div className="flex flex-col gap-4">
            <Input
              label="ID"
              type="text"
              placeholder="question_id"
              maxLength={TAG_MAX}
              value={settings.tagValue}
              error={settings.idError}
              onChange={(event) => settings.onTagChange(sanitizeQuestionId(event.target.value))}
            />
            <Input
              label="Title"
              type="text"
              placeholder="Enter a title (optional)"
              maxLength={80}
              value={settings.titleValue}
              onChange={(event) => settings.onTitleChange(event.target.value)}
            />
            {settings.required !== undefined && settings.onRequiredChange && (
              <Toggle
                label="Required"
                checked={settings.required}
                onChange={settings.onRequiredChange}
              />
            )}
          </div>
        </Modal>
      )}
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
  const [isIdEditMode, setIsIdEditMode] = useState(false);

  const handleSubmit = () => {
    setIsIdEditMode(false);
  };

  return (
    <div className="flex flex-col items-start gap-1">
      <div className="flex items-center gap-1.5">
        <Tooltip
          title="Identifier for this question. Lowercase only; no spaces or capitals."
          size="sm"
        >
          <span
            className={`text-[0.78rem] font-medium text-muted-foreground ${isEditMode ? "cursor-pointer hover:text-foreground" : ""}`}
            onClick={isEditMode ? () => setIsIdEditMode(true) : undefined}
          >
            {tagValue || "—"}
          </span>
        </Tooltip>
        {isEditMode && (
          <Button
            className="p-1!"
            type="button"
            variant="ghost"
            size="xxs"
            onClick={() => setIsIdEditMode(true)}
            aria-label="Edit ID"
          >
            ✎
          </Button>
        )}
      </div>
      {idError && (
        <span className="text-[0.78rem] text-destructive">{idError}</span>
      )}
      <Modal
        open={isIdEditMode}
        onClose={() => setIsIdEditMode(false)}
        title="Edit ID"
        width={420}
        footer={(
          <>
            <Button type="button" variant="secondary" onClick={() => setIsIdEditMode(false)}>
              Cancel
            </Button>
            <Button type="button" variant="primary" onClick={handleSubmit}>
              Save
            </Button>
          </>
        )}
      >
        <Input
          label="ID"
          type="text"
          placeholder="question_id"
          maxLength={TAG_MAX}
          value={tagValue}
          onChange={(event) => onTagChange(sanitizeQuestionId(event.target.value))}
          onKeyDown={(event) => {
            if (event.key === "Enter") handleSubmit();
            if (event.key === "Escape") setIsIdEditMode(false);
          }}
          autoFocus
        />
      </Modal>
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
  idField?: ReactNode;
  titleValue?: string;
  onTitleChange?: (next: string) => void;
  titleMax?: number;
  showTitleEdit?: boolean;
  validationError?: string;
};

export function NodePillQuestionField({
  value,
  onChange,
  isEditMode,
  max,
  idField,
  titleValue,
  onTitleChange,
  titleMax = 80,
  showTitleEdit = false,
  validationError,
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
      {isEditMode && idField && <div className="mb-1.5">{idField}</div>}
      <div className="mb-2 flex items-center gap-1.5">
        <span
          className={`${nodePillLabelClass} ${hasTitle && showTitleEdit && isEditMode ? "cursor-pointer hover:text-foreground" : ""}`}
          onClick={hasTitle && showTitleEdit && isEditMode ? handleTitleClick : undefined}
        >
          {hasTitle && titleValue ? titleValue : "Question"}
        </span>
        {hasTitle && showTitleEdit && isEditMode && (
          <Button
            className="mt-1 p-1!"
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
          shellClassName={validationError ? "ring-2 ring-destructive ring-offset-0" : undefined}
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
        {validationError && (
          <span className="text-[0.78rem] text-destructive">{validationError}</span>
        )}
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

type DragThresholdsProps = {
  itemId: string;
  isDragging: boolean;
  thresholdRatio: number | null;
  activeDrag: unknown;
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
  onExpandInEditMode: () => void;
};

export function NodePillCollapsed({ family, tagValue, title, onExpand, onExpandInEditMode }: CollapsedProps) {
  void title;
  const { leading } = useContext(MobileControlsContext);
  return (
    <div className={nodePillCollapsedShellClass}>
      <div className="flex items-center gap-3 px-3.5 py-3.5">
        {leading && (
          <span className="hidden max-[640px]:flex items-center">{leading}</span>
        )}
        <Badge variant="accent" size="md">{family}</Badge>
        <div
          className="flex min-w-0 flex-1 cursor-pointer items-baseline justify-end overflow-hidden"
          onClick={onExpand}
        >
          <span className="overflow-hidden text-ellipsis whitespace-nowrap text-[0.78rem] text-muted-foreground">
            {tagValue}
          </span>
        </div>
        <Button
          type="button"
          variant="secondary"
          size="xs"
          onClick={onExpandInEditMode}
        >
          Edit
        </Button>
      </div>
    </div>
  );
}

export { nodePillShellClass, nodePillShellEditClass, nodePillBodyClass, nodePillFieldClass } from "./nodePillStyles";
