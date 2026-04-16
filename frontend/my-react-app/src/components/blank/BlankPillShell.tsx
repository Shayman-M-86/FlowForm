import type { ReactNode } from "react";
import { useState } from "react";
import { TAG_MAX, blurOnEnter } from "./blankPillUtils";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { LargeInput } from "../ui/LargeInput";
import { Modal } from "../ui/Modal";
import { Tooltip } from "../ui/Tooltip";

type TopbarProps = {
  family: string;
  tagValue: string;
  onTagChange: (next: string) => void;
  isEditMode: boolean;
  onToggleEditMode: () => void;
  onDelete?: () => void;
  actions?: ReactNode;
};

export function BlankPillTopbar({
  family,
  tagValue,
  onTagChange,
  isEditMode,
  onToggleEditMode,
  onDelete,
  actions,
}: TopbarProps) {
  return (
    <header className="blank-pill__topbar">
      <div className="blank-pill__topbar-left">
        <Badge variant="accent" size="xl">{family}</Badge>
        <div className="blank-pill__id-label">
          <h3 className="blank-pill__id">id</h3>
          <Input
            type="text"
            placeholder={isEditMode ? "question_id" : ""}
            value={tagValue}
            size="xs"
            maxLength={TAG_MAX}
            readOnly={!isEditMode}
            variant="quiet"
            pill
            onChange={(event) => onTagChange(event.target.value)}
            onKeyDown={blurOnEnter}
          />
        </div>
      </div>
      <div className="blank-pill__actions">
        {isEditMode && (actions ?? (
          <>
            <Button
              className="blank-pill__action"
              type="button"
              variant="danger"
              size="xs"
              pill
              onClick={onDelete}
            >
              Delete
            </Button>
            <Button className="blank-pill__action" type="button" variant="quiet" size="xs" pill>
              Settings
            </Button>
          </>
        ))}
        <Button
          className={`blank-pill__action ${isEditMode ? "blank-pill__action--active" : ""}`}
          type="button"
          variant={isEditMode ? "secondary" : "quiet"}
          size="xs"
          pill
          onClick={onToggleEditMode}
        >
          {isEditMode ? "Editing" : "Edit"}
        </Button>
      </div>
    </header>
  );
}

type TitleFieldProps = {
  value: string;
  onChange: (next: string) => void;
  isEditMode: boolean;
  max?: number;
};

export function BlankPillTitleField({
  value,
  onChange,
  isEditMode,
  max = 80,
}: TitleFieldProps) {
  return (
    <div className="blank-pill__field">
      <div className="blank-pill__title-stack">
        <Input
          className="blank-pill__title-field"
          type="text"
          placeholder="Enter a title (optional)"
          maxLength={max}
          value={value}
          readOnly={!isEditMode}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={blurOnEnter}
        />
        {isEditMode && value.length === max && (
          <span className="blank-pill__title-limit">
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

export function BlankPillQuestionField({
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
    <div className="blank-pill__field">
      <div className="blank-pill__question-header">
        <span className="blank-pill__label">
          {hasTitle && titleValue ? titleValue : "Question"}
        </span>
        {hasTitle && showTitleEdit && isEditMode && (
          <Button
            className="blank-pill__title-edit-btn"
            type="button"
            variant="ghost"
            size="xs"
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
            className="blank-pill__title-edit-input-field"
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
      <div className="blank-pill__question-stack">
        <LargeInput
          className="blank-pill__question-field"
          placeholder="Type your question here"
          rows={3}
          size="sm"
          autoGrow
          maxAutoGrowHeight={680}
          maxText={max}
          value={value}
          readOnly={!isEditMode}
          onChange={(event) => onChange(event.target.value)}
        />
        {isEditMode && value.length === max && (
          <span className="blank-pill__question-limit">
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

export function BlankPillCharCount({ label, value, max, tooltip }: CharCountProps) {
  const labelNode = tooltip ? (
    <Tooltip title={tooltip} size="sm">
      <span className="blank-pill__char-count-label">{label}</span>
    </Tooltip>
  ) : (
    <span className="blank-pill__char-count-label">{label}</span>
  );

  return (
    <span className="blank-pill__char-count">
      <span className="blank-pill__char-count-item">
        {labelNode}
        <span className="blank-pill__char-count-value">{value}</span>
      </span>
      {max !== undefined && (
        <>
          <span className="blank-pill__char-count-divider">/</span>
          <span className="blank-pill__char-count-item">
            <span className="blank-pill__char-count-label">Max</span>
            <span className="blank-pill__char-count-value">{max}</span>
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

export function BlankPillFieldHead({ label, children }: FieldHeadProps) {
  return (
    <span className="blank-pill__field-head">
      <span className="blank-pill__label">{label}</span>
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

export function BlankPillDragThresholds({
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
