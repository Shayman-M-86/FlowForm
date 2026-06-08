import { useEffect, useState } from "react";
import "./RatingQuestion.css";
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
  nodePillPanelClass,
  nodePillPreviewClass,
  nodePillShellClass,
  nodePillShellEditClass,
} from "../nodePillStyles";
import { Input, NumberStepper, NumberStepperGroup, Select, Toggle } from "@flowform/ui";
import type { RatingContent, EmojiListType } from "../questionTypes";
import type { CreateQuestionNodeRequest } from "@flowform/schema";

export type RatingQuestionNode = Omit<CreateQuestionNodeRequest, "content"> & {
  content: RatingContent;
};

interface RatingQuestionProps {
  node: RatingQuestionNode;
  onChange: (next: RatingQuestionNode) => void;
  onDelete?: () => void;
  idError?: string;
  validationError?: string;
  isCollapsed?: boolean;
  isEditMode?: boolean;
  onExpand?: () => void;
  onExpandInEditMode?: () => void;
  onEditModeChange?: (isEditMode: boolean) => void;
}

const controlClass = "flex min-w-0 flex-col gap-2";
const controlLabelClass =
  "text-[0.78rem] font-semibold uppercase tracking-[0.04em] text-muted-foreground";

const MAX_STARS = 12;

type RatingType = "numeric-slider" | "emoji" | "stars";

const RATING_TYPE_OPTIONS: Array<{ value: RatingType; label: string }> = [
  { value: "numeric-slider", label: "Numeric slider" },
  { value: "emoji", label: "Emoji scale" },
  { value: "stars", label: "Star rating" },
];

type EmojiScaleType = "sad" | "angry" | "disgust";

const EMOJI_SCALES: Record<EmojiScaleType, Array<{ value: number; emoji: string; label: string }>> =
  {
    sad: [
      { value: 1, emoji: "😢", label: "Very sad" },
      { value: 2, emoji: "🙁", label: "Sad" },
      { value: 3, emoji: "😐", label: "Neutral" },
      { value: 4, emoji: "🙂", label: "Happy" },
      { value: 5, emoji: "😄", label: "Very happy" },
    ],
    angry: [
      { value: 1, emoji: "🤬", label: "Very angry" },
      { value: 2, emoji: "😠", label: "Angry" },
      { value: 3, emoji: "😐", label: "Neutral" },
      { value: 4, emoji: "🙂", label: "Happy" },
      { value: 5, emoji: "😄", label: "Very happy" },
    ],
    disgust: [
      { value: 1, emoji: "🤢", label: "Very disgusted" },
      { value: 2, emoji: "😖", label: "Disgusted" },
      { value: 3, emoji: "😐", label: "Neutral" },
      { value: 4, emoji: "🙂", label: "Happy" },
      { value: 5, emoji: "😄", label: "Very happy" },
    ],
  };

function StarIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 1.8l3.145 6.375 7.037 1.022-5.091 4.962 1.202 7.01L12 17.861l-6.293 3.308 1.202-7.01L1.818 9.197l7.037-1.022L12 1.8z" />
    </svg>
  );
}

function getValidSteps(rangeStart: number, rangeEnd: number) {
  const span = Math.abs(rangeEnd - rangeStart);
  if (span === 0) return [1];

  const steps: number[] = [];
  for (let candidate = 1; candidate <= span; candidate += 1) {
    if (span % candidate === 0) {
      steps.push(candidate);
    }
  }
  return steps;
}

function getNearestValidStep(nextStep: number, validSteps: number[]) {
  return validSteps.reduce((closest, current) => {
    const currentDistance = Math.abs(current - nextStep);
    const closestDistance = Math.abs(closest - nextStep);
    if (currentDistance < closestDistance) return current;
    if (currentDistance === closestDistance && current < closest) return current;
    return closest;
  }, validSteps[0]);
}

function contentToRatingType(content: RatingContent): RatingType {
  switch (content.definition.variant) {
    case "slider":
      return "numeric-slider";
    case "emoji":
      return "emoji";
    case "stars":
      return "stars";
  }
}

function contentToEmojiScaleType(content: RatingContent): EmojiScaleType {
  if (content.definition.variant !== "emoji") return "sad";
  switch (content.definition.emoji_list) {
    case "angry_to_happy":
      return "angry";
    case "disgust_to_happy":
      return "disgust";
    default:
      return "sad";
  }
}

function getEmojiListType(scaleType: EmojiScaleType): EmojiListType {
  switch (scaleType) {
    case "sad":
      return "sad_to_happy";
    case "angry":
      return "angry_to_happy";
    case "disgust":
      return "disgust_to_happy";
  }
}

function alignToStep(value: number, min: number, max: number, step: number) {
  const safeStep = Math.max(1, Math.abs(step) || 1);
  const clamped = Math.min(max, Math.max(min, value));
  const stepped = min + Math.round((clamped - min) / safeStep) * safeStep;
  return Math.min(max, Math.max(min, stepped));
}

export function RatingQuestion({
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
}: RatingQuestionProps) {
  const { content } = node;
  const titleValue = content.title ?? "";
  const questionValue = content.label;

  const ratingType = contentToRatingType(content);
  const rangeStart = content.definition.variant === "slider" ? content.definition.range.min : -5;
  const rangeEnd = content.definition.variant === "slider" ? content.definition.range.max : 5;
  const stepValue = content.definition.variant === "slider" ? content.definition.range.step : 1;
  const leftLabel = content.definition.ui.left_label;
  const rightLabel = content.definition.ui.right_label;
  const starCount = content.definition.variant === "stars" ? content.definition.stars : 5;
  const emojiScaleType = contentToEmojiScaleType(content);
  const showEmojiWords =
    content.definition.variant === "emoji" ? (content.definition.words ?? true) : true;

  const [sliderValue, setSliderValue] = useState(rangeStart);
  const [starValue, setStarValue] = useState(0);
  const [emojiValue, setEmojiValue] = useState(0);

  const validSteps = getValidSteps(rangeStart, rangeEnd);
  const safeStepValue = getNearestValidStep(Math.max(1, Math.abs(stepValue) || 1), validSteps);
  const currentStepIndex = validSteps.indexOf(safeStepValue);
  const normalizedSliderValue = alignToStep(sliderValue, rangeStart, rangeEnd, safeStepValue);
  const stepCount = Math.max(0, Math.floor((rangeEnd - rangeStart) / safeStepValue));
  const tickCount = Math.min(stepCount + 1, 101);
  const sliderRatio =
    rangeEnd === rangeStart
      ? 0
      : (normalizedSliderValue - rangeStart) / (rangeEnd - rangeStart);
  const tickValues = Array.from({ length: tickCount }, (_, index) => {
    if (tickCount === 1) return rangeStart;
    if (index === tickCount - 1) return rangeEnd;
    return rangeStart + index * safeStepValue;
  });

  useEffect(() => {
    setSliderValue((current) => alignToStep(current, rangeStart, rangeEnd, safeStepValue));
  }, [rangeStart, rangeEnd, safeStepValue]);

  useEffect(() => {
    setStarValue((current) => Math.min(starCount, Math.max(0, current)));
  }, [starCount]);

  function updateContent(update: (current: RatingContent) => RatingContent) {
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

  function updateRatingType(nextType: RatingType) {
    updateContent((current) => {
      const ui = { left_label: current.definition.ui.left_label, right_label: current.definition.ui.right_label };
      switch (nextType) {
        case "numeric-slider":
          return { ...current, definition: { variant: "slider", range: { min: -5, max: 5, step: 1 }, ui } };
        case "emoji":
          return { ...current, definition: { variant: "emoji", emoji_list: getEmojiListType(emojiScaleType), words: showEmojiWords, ui } };
        case "stars":
          return { ...current, definition: { variant: "stars", stars: 5, ui } };
      }
    });
  }

  function updateRangeStart(nextValue: number) {
    if (content.definition.variant !== "slider") return;
    const next = Math.min(1000, Math.max(-1000, Math.round(nextValue)));
    updateContent((current) => {
      if (current.definition.variant !== "slider") return current;
      return {
        ...current,
        definition: {
          ...current.definition,
          range: {
            ...current.definition.range,
            min: next,
            max: Math.max(current.definition.range.max, next),
          },
        },
      };
    });
  }

  function updateRangeEnd(nextValue: number) {
    if (content.definition.variant !== "slider") return;
    const next = Math.min(1000, Math.max(-1000, Math.round(nextValue)));
    updateContent((current) => {
      if (current.definition.variant !== "slider") return current;
      return {
        ...current,
        definition: {
          ...current.definition,
          range: {
            ...current.definition.range,
            max: next,
            min: Math.min(current.definition.range.min, next),
          },
        },
      };
    });
  }

  function updateStep(nextStep: number) {
    if (content.definition.variant !== "slider") return;
    updateContent((current) => {
      if (current.definition.variant !== "slider") return current;
      return {
        ...current,
        definition: {
          ...current.definition,
          range: { ...current.definition.range, step: nextStep },
        },
      };
    });
  }

  function updateLeftLabel(value: string) {
    updateContent((current) => ({
      ...current,
      definition: { ...current.definition, ui: { ...current.definition.ui, left_label: value } },
    }));
  }

  function updateRightLabel(value: string) {
    updateContent((current) => ({
      ...current,
      definition: { ...current.definition, ui: { ...current.definition.ui, right_label: value } },
    }));
  }

  function updateStarCount(nextValue: number) {
    if (content.definition.variant !== "stars") return;
    const nextCount = Math.min(MAX_STARS, Math.max(1, Math.round(nextValue) || 1));
    updateContent((current) => {
      if (current.definition.variant !== "stars") return current;
      return { ...current, definition: { ...current.definition, stars: nextCount } };
    });
  }

  function updateEmojiScaleType(nextScale: EmojiScaleType) {
    updateContent((current) => {
      if (current.definition.variant !== "emoji") return current;
      return {
        ...current,
        definition: { ...current.definition, emoji_list: getEmojiListType(nextScale) },
      };
    });
  }

  function updateShowEmojiWords(next: boolean) {
    updateContent((current) => {
      if (current.definition.variant !== "emoji") return current;
      return { ...current, definition: { ...current.definition, words: next } };
    });
  }

  function selectStarValue(nextValue: number) {
    setStarValue((current) => (current === nextValue ? 0 : nextValue));
  }

  function selectEmojiValue(nextValue: number) {
    setEmojiValue((current) => (current === nextValue ? 0 : nextValue));
  }

  function toggleEditMode() {
    onEditModeChange?.(!isEditMode);
  }

  const emojiScale = EMOJI_SCALES[emojiScaleType];
  const selectedEmoji = emojiScale.find((option) => option.value === emojiValue);
  const rangePreview =
    rangeStart === rangeEnd ? `${rangeStart}` : `${rangeStart} to ${rangeEnd}`;
  const scaleSummary =
    ratingType === "stars"
      ? `0 to ${starCount}`
      : ratingType === "emoji"
        ? `0 to ${emojiScale.length}`
        : rangePreview;

  if (isCollapsed) {
    return (
      <NodePillCollapsed
        family="Rating"
        tagValue={node.node_key}
        title={titleValue}
        onExpand={() => onExpand?.()}
        onExpandInEditMode={() => onExpandInEditMode?.()}
      />
    );
  }

  return (
    <section
      className={`${nodePillShellClass} ${isEditMode ? nodePillShellEditClass : ""} rating-question`}
      aria-label="Rating question"
    >
      <NodePillTopbar
        family="Rating"
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
          validationError={
            validationError && !questionValue.trim() ? validationError : undefined
          }
        />

        <div className={nodePillFieldClass}>
          {isEditMode && (
            <NodePillFieldHead label="Rating">
              <NodePillCharCount label="Range" value={scaleSummary} />
            </NodePillFieldHead>
          )}

          <div className={`${nodePillPanelClass} rating-question__panel`}>
            {isEditMode && (
              <>
                <div className="flex flex-wrap items-start gap-4">
                  <Select
                    className={controlClass}
                    label="Type"
                    value={ratingType}
                    disabled={!isEditMode}
                    options={RATING_TYPE_OPTIONS}
                    onChange={(event) => updateRatingType(event.target.value as RatingType)}
                  />
                  {ratingType === "stars" ? (
                    <div className={controlClass}>
                      <span className={controlLabelClass}>Stars</span>
                      <NumberStepper
                        className="self-start"
                        ariaLabel="Star count"
                        size="sm"
                        variant="primary"
                        allowInput
                        value={starCount}
                        min={1}
                        max={MAX_STARS}
                        disabled={!isEditMode}
                        onChange={updateStarCount}
                      />
                    </div>
                  ) : ratingType === "emoji" ? (
                    <>
                      <Select
                        className={`${controlClass} flex-1 min-w-60`}
                        label="Emoji list"
                        value={emojiScaleType}
                        disabled={!isEditMode}
                        options={[
                          { value: "sad", label: "Sad to happy" },
                          { value: "angry", label: "Angry to happy" },
                          { value: "disgust", label: "Disgust to happy" },
                        ]}
                        onChange={(event) =>
                          updateEmojiScaleType(event.target.value as EmojiScaleType)
                        }
                      />
                      <div className={controlClass}>
                        <span className={controlLabelClass}>Words</span>
                        <Toggle
                          label="Show words"
                          checked={showEmojiWords}
                          disabled={!isEditMode}
                          onChange={updateShowEmojiWords}
                        />
                      </div>
                    </>
                  ) : (
                    <>
                      <div className={`${controlClass} flex-1 min-w-60`}>
                        <span className={controlLabelClass}>Range</span>
                        <NumberStepperGroup
                          className="self-start"
                          ariaLabel="Slider range"
                          size="sm"
                          variant="primary"
                          allowInput
                          items={[
                            {
                              key: "from",
                              label: "From",
                              value: rangeStart,
                              min: -1000,
                              max: 1000,
                              disabled: !isEditMode,
                            },
                            {
                              key: "to",
                              label: "To",
                              value: rangeEnd,
                              min: -1000,
                              max: 1000,
                              disabled: !isEditMode,
                            },
                          ]}
                          onChange={(key, value) => {
                            if (key === "from") {
                              updateRangeStart(value);
                            } else {
                              updateRangeEnd(value);
                            }
                          }}
                        />
                      </div>

                      <div className={controlClass}>
                        <span className={controlLabelClass}>Step</span>
                        <NumberStepper
                          className="self-start"
                          ariaLabel="Slider step"
                          size="sm"
                          variant="primary"
                          value={safeStepValue}
                          min={validSteps[0]}
                          max={validSteps[validSteps.length - 1]}
                          disabled={!isEditMode}
                          canDecrement={currentStepIndex > 0}
                          canIncrement={currentStepIndex < validSteps.length - 1}
                          onDecrement={() =>
                            updateStep(validSteps[Math.max(0, currentStepIndex - 1)])
                          }
                          onIncrement={() =>
                            updateStep(
                              validSteps[Math.min(validSteps.length - 1, currentStepIndex + 1)],
                            )
                          }
                          onChange={(value) =>
                            updateStep(
                              getNearestValidStep(Math.max(1, Math.abs(value) || 1), validSteps),
                            )
                          }
                        />
                      </div>
                    </>
                  )}
                </div>

                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <Input
                    className="min-w-0"
                    label="Left label"
                    type="text"
                    placeholder="Low-end label"
                    value={leftLabel}
                    maxLength={50}
                    disabled={!isEditMode}
                    onChange={(event) => updateLeftLabel(event.target.value)}
                    onKeyDown={blurOnEnter}
                  />

                  <Input
                    className="min-w-0"
                    label="Right label"
                    type="text"
                    placeholder="High-end label"
                    value={rightLabel}
                    maxLength={50}
                    disabled={!isEditMode}
                    onChange={(event) => updateRightLabel(event.target.value)}
                    onKeyDown={blurOnEnter}
                  />
                </div>
              </>
            )}

            <div className={`${nodePillPreviewClass} `}>
              <div className="text-base text-foreground">
                Current value:{" "}
                <strong>
                  {ratingType === "stars"
                    ? `${starValue} / ${starCount}`
                    : ratingType === "emoji"
                      ? selectedEmoji
                        ? `${selectedEmoji.emoji}${showEmojiWords ? ` ${selectedEmoji.label}` : ""}`
                        : "None"
                      : normalizedSliderValue}
                </strong>
              </div>
              <div className="flex justify-between gap-4 text-sm text-muted-foreground [&>span:last-child]:text-right">
                <span>{leftLabel || "Left label"}</span>
                <span>{rightLabel || "Right label"}</span>
              </div>
              {ratingType === "stars" ? (
                <div
                  className="rating-question__stars"
                  role="radiogroup"
                  aria-label="Star rating"
                  style={{ "--rating-star-count": starCount } as React.CSSProperties}
                >
                  {Array.from({ length: starCount }, (_, index) => {
                    const nextFullValue = index + 1;
                    const nextHalfValue = index + 0.5;
                    const fillLevel = Math.max(0, Math.min(1, starValue - index));
                    return (
                      <div
                        key={nextFullValue}
                        className="rating-question__star"
                        role="radio"
                        aria-checked={
                          nextFullValue === starValue || nextHalfValue === starValue
                        }
                        aria-label={`${nextFullValue} star${nextFullValue === 1 ? "" : "s"}`}
                      >
                        <span className="rating-question__star-base" aria-hidden="true">
                          <span className="rating-question__star-glyph">
                            <StarIcon />
                          </span>
                        </span>
                        <span
                          className="rating-question__star-fill"
                          aria-hidden="true"
                          style={{ width: `${fillLevel * 100}%` }}
                        >
                          <span className="rating-question__star-glyph">
                            <StarIcon />
                          </span>
                        </span>
                        <button
                          className="rating-question__star-hit rating-question__star-hit--left"
                          type="button"
                          aria-label={`${nextHalfValue} stars`}
                          disabled={!isEditMode}
                          onClick={() => selectStarValue(nextHalfValue)}
                        />
                        <button
                          className="rating-question__star-hit rating-question__star-hit--right"
                          type="button"
                          aria-label={`${nextFullValue} stars`}
                          disabled={!isEditMode}
                          onClick={() => selectStarValue(nextFullValue)}
                        />
                      </div>
                    );
                  })}
                </div>
              ) : ratingType === "emoji" ? (
                <div
                  className={`rating-question__emoji-list ${!showEmojiWords ? "rating-question__emoji-list--icons-only" : ""}`}
                  role="radiogroup"
                  aria-label="Emoji scale"
                >
                  {emojiScale.map((option) => (
                    <button
                      key={option.value}
                      className={`rating-question__emoji-option ${emojiValue === option.value ? "rating-question__emoji-option--active" : ""}`}
                      type="button"
                      role="radio"
                      aria-checked={emojiValue === option.value}
                      aria-label={option.label}
                      disabled={!isEditMode}
                      onClick={() => selectEmojiValue(option.value)}
                    >
                      <span className="rating-question__emoji-glyph" aria-hidden="true">
                        {option.emoji}
                      </span>
                      {showEmojiWords && (
                        <span className="rating-question__emoji-label">{option.label}</span>
                      )}
                    </button>
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-[auto_1fr_auto] items-center gap-3.5">
                  <span className="min-w-7 text-center text-[0.88rem] font-semibold text-foreground">
                    {rangeStart}
                  </span>
                  <div className="relative h-6.5 rating-question__preview-line">
                    <div className="rating-question__slider-track" aria-hidden="true" />
                    <div className="rating-question__slider-ticks" aria-hidden="true">
                      {tickValues.map((tickValue) => (
                        <span key={tickValue} className="rating-question__slider-tick" />
                      ))}
                    </div>
                    <div
                      className="rating-question__slider-visual-thumb"
                      aria-hidden="true"
                      style={{ left: `calc(10px + (100% - 20px) * ${sliderRatio})` }}
                    />
                    <input
                      className="rating-question__slider"
                      type="range"
                      min={rangeStart}
                      max={rangeEnd}
                      step={safeStepValue}
                      value={normalizedSliderValue}
                      disabled={!isEditMode}
                      onChange={(event) => {
                        setSliderValue(
                          alignToStep(
                            Number(event.target.value),
                            rangeStart,
                            rangeEnd,
                            safeStepValue,
                          ),
                        );
                      }}
                    />
                  </div>
                  <span className="min-w-7 text-center text-sm font-semibold text-foreground">
                    {rangeEnd}
                  </span>
                </div>
              )}
              {isEditMode && (
                <div className="flex justify-between gap-4 text-sm text-muted-foreground [&>span:last-child]:text-right">
                  <span>
                    {RATING_TYPE_OPTIONS.find((option) => option.value === ratingType)?.label}
                  </span>
                  <span>
                    {ratingType === "stars"
                      ? `${starCount} stars`
                      : ratingType === "emoji"
                        ? `${emojiScaleType === "sad" ? "Sad" : emojiScaleType === "angry" ? "Angry" : "Disgust"} to happy`
                        : `Step ${stepValue}`}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
