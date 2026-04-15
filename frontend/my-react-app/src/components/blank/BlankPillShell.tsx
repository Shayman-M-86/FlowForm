import type { ReactNode } from "react";
import { useState } from "react";
import { TAG_MAX, autoResizeTextarea, blurOnEnter } from "./blankPillUtils";

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
        <span className="blank-pill__family">{family}</span>
        <input
          className={`blank-pill__topbar-tag ${!isEditMode ? "blank-pill__topbar-tag--view" : ""}`}
          type="text"
          placeholder={isEditMode ? "question_id" : ""}
          value={tagValue}
          maxLength={TAG_MAX}
          size={Math.max(11, tagValue.length + 2)}
          readOnly={!isEditMode}
          onChange={(event) => onTagChange(event.target.value)}
          onKeyDown={blurOnEnter}
        />
      </div>
      <div className="blank-pill__actions">
        {isEditMode && (actions ?? (
          <>
            <button
              className="blank-pill__action blank-pill__action--danger"
              type="button"
              onClick={onDelete}
            >
              Delete
            </button>
            <button className="blank-pill__action" type="button">
              Settings
            </button>
          </>
        ))}
        <button
          className={`blank-pill__action ${isEditMode ? "blank-pill__action--active" : ""}`}
          type="button"
          onClick={onToggleEditMode}
        >
          {isEditMode ? "Editing" : "Edit"}
        </button>
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
      {/* <span className="blank-pill__label">Title</span> */}
      <div className="blank-pill__title-stack">
        <div className="blank-pill__title-field">
          <input
            className="blank-pill__title"
            type="text"
            placeholder="Enter a title (optional)"
            maxLength={max}
            value={value}
            readOnly={!isEditMode}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={blurOnEnter}
          />
        </div>
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
          <button
            className="blank-pill__title-edit-btn"
            type="button"
            onClick={handleTitleClick}
            title="Edit title"
          >
            ✎
          </button>
        )}
      </div>
      {isTitleEditMode && hasTitle && (
        <div className="blank-pill__title-edit-modal">
          <div className="blank-pill__title-edit-content">
            <label className="blank-pill__title-edit-label">Enter Title</label>
            <input
              type="text"
              className="blank-pill__title-edit-input"
              placeholder="Enter a title (optional)"
              maxLength={titleMax}
              value={titleValue}
              onChange={(event) => onTitleChange(event.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleTitleSubmit();
                if (e.key === "Escape") setIsTitleEditMode(false);
              }}
              autoFocus
            />
            <div className="blank-pill__title-edit-buttons">
              <button
                className="blank-pill__title-edit-btn-cancel"
                type="button"
                onClick={() => setIsTitleEditMode(false)}
              >
                Cancel
              </button>
              <button
                className="blank-pill__title-edit-btn-save"
                type="button"
                onClick={handleTitleSubmit}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
      <div className="blank-pill__question-stack">
        <div className="blank-pill__question-field">
          <textarea
            className="blank-pill__question"
            placeholder="Type your question here"
            rows={3}
            maxLength={max}
            value={value}
            readOnly={!isEditMode}
            onChange={(event) => onChange(event.target.value)}
            onInput={(event) => autoResizeTextarea(event.currentTarget)}
          />
        </div>
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
  return (
    <span className="blank-pill__char-count">
      <span className="blank-pill__char-count-item">
        <span
          className="blank-pill__char-count-label"
          {...(tooltip ? { "data-tooltip": tooltip } : {})}
        >
          {label}
        </span>
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

type DragLockState = {
  siblingId: string;
  direction: "down" | "up";
};

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
  const returnRatio = resolveLockRatio(activeDrag?.reverseLock ?? null, itemId, "reverse");
  const insertRatio = resolveLockRatio(activeDrag?.insertLock ?? null, itemId, "insert");

  return (
    <>
      {thresholdRatio !== null && !isDragging && (
        <>
          <div
            className="blank-pill__option-threshold-line"
            style={{ top: `${thresholdRatio * 100}%` }}
          />
          <div className="blank-pill__option-threshold-label">
            {thresholdRatio.toFixed(2)}
          </div>
        </>
      )}
      {returnRatio !== null && (
        <>
          <div
            className="blank-pill__option-threshold-line blank-pill__option-threshold-line--return"
            style={{ top: `${returnRatio * 100}%` }}
          />
          <div className="blank-pill__option-threshold-label blank-pill__option-threshold-label--return">
            {returnRatio.toFixed(2)}
          </div>
        </>
      )}
      {insertRatio !== null && (
        <>
          <div
            className="blank-pill__option-threshold-line blank-pill__option-threshold-line--insert-lock"
            style={{ top: `${insertRatio * 100}%` }}
          />
          <div className="blank-pill__option-threshold-label blank-pill__option-threshold-label--insert-lock">
            {insertRatio.toFixed(2)}
          </div>
        </>
      )}
    </>
  );
}

function resolveLockRatio(
  lock: DragLockState | null,
  itemId: string,
  kind: "reverse" | "insert",
): number | null {
  if (!lock || lock.siblingId !== itemId) return null;
  if (kind === "reverse") {
    return lock.direction === "down" ? 0.85 : 0.15;
  }
  return lock.direction === "down" ? 0.15 : 0.85;
}
