import { useEffect, useState, forwardRef, useImperativeHandle } from "react";
import "./RatingQuestion.css";
import { QUESTION_MAX, blurOnEnter } from "./NodePillUtils";
import { NodePillTopbar, NodePillQuestionField, NodePillCharCount, NodePillFieldHead, NodePillCollapsed } from "./NodePillShell";
import {
  nodePillBodyClass,
  nodePillFieldClass,
  nodePillPanelClass,
  nodePillPreviewClass,
  nodePillShellClass,
  nodePillShellEditClass,
} from "./nodePillStyles";
import { Input, NumberStepper, NumberStepperGroup, Select, Toggle } from "@flowform/ui";
import type { RatingContent, EmojiListType } from "./questionTypes";

const controlClass = "flex min-w-0 flex-col gap-2";
const controlLabelClass = "text-[0.78rem] font-semibold uppercase tracking-[0.04em] text-muted-foreground";

const MAX_STARS = 12;

type RatingType = "numeric-slider" | "emoji" | "stars";

export interface RatingQuestionHandle {
  getData(): RatingContent;
}

interface RatingQuestionProps {
  onDelete?: () => void;
  title?: string;
  initialTag?: string;
  initialContent?: RatingContent;
  idError?: string;
  isCollapsed?: boolean;
  onExpand?: () => void;
  onEditModeChange?: (isEditMode: boolean) => void;
  onDataChange?: (content: RatingContent) => void;
}

const RATING_TYPE_OPTIONS: Array<{ value: RatingType; label: string }> = [
  { value: "numeric-slider", label: "Numeric slider" },
  { value: "emoji", label: "Emoji scale" },
  { value: "stars", label: "Star rating" },
];

type EmojiScaleType = "sad" | "angry" | "disgust";

const EMOJI_SCALES: Record<EmojiScaleType, Array<{ value: number; emoji: string; label: string }>> = {
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

export const RatingQuestion = forwardRef<RatingQuestionHandle, RatingQuestionProps>(function RatingQuestion({ onDelete, title, initialTag, initialContent, idError, isCollapsed, onExpand, onEditModeChange, onDataChange }, ref) {
  const initialRatingType: RatingType =
    initialContent?.definition.variant === "slider"
      ? "numeric-slider"
      : initialContent?.definition.variant === "emoji"
        ? "emoji"
        : initialContent?.definition.variant === "star"
          ? "stars"
          : "numeric-slider";
  const [isEditMode, setIsEditMode] = useState(true);
  const [titleValue, setTitleValue] = useState(initialContent?.title ?? title ?? "");
  const [questionValue, setQuestionValue] = useState(initialContent?.label ?? "");
  const [tagValue, setTagValue] = useState(initialContent?.id ?? initialTag ?? "question_id_1");
  const [ratingType, setRatingType] = useState<RatingType>(initialRatingType);
  const [rangeStart, setRangeStart] = useState(initialContent?.definition.variant === "slider" ? initialContent.definition.range.min : -5);
  const [rangeEnd, setRangeEnd] = useState(initialContent?.definition.variant === "slider" ? initialContent.definition.range.max : 5);
  const [leftLabel, setLeftLabel] = useState(initialContent?.definition.ui.left_label ?? "Strongly disagree");
  const [rightLabel, setRightLabel] = useState(initialContent?.definition.ui.right_label ?? "Strongly agree");
  const [stepValue, setStepValue] = useState(initialContent?.definition.variant === "slider" ? initialContent.definition.range.step : 1);
  const [sliderValue, setSliderValue] = useState(initialContent?.definition.variant === "slider" ? initialContent.definition.range.min : 0);
  const [starCount, setStarCount] = useState(initialContent?.definition.variant === "star" ? initialContent.definition.stars : 5);
  const [starValue, setStarValue] = useState(0);
  const [emojiValue, setEmojiValue] = useState(0);
  const [emojiScaleType, setEmojiScaleType] = useState<EmojiScaleType>(
    initialContent?.definition.variant === "emoji"
      ? initialContent.definition.emoji_list === "angry_to_happy"
        ? "angry"
        : initialContent.definition.emoji_list === "disgust_to_happy"
          ? "disgust"
          : "sad"
      : "sad",
  );
  const [showEmojiWords, setShowEmojiWords] = useState(initialContent?.definition.variant === "emoji" ? initialContent.definition.words : true);

  function getEmojiListType(): EmojiListType {
    switch (emojiScaleType) {
      case "sad":
        return "sad_to_happy";
      case "angry":
        return "angry_to_happy";
      case "disgust":
        return "disgust_to_happy";
    }
  }

  const ratingQuestionData: RatingContent =
    ratingType === "numeric-slider"
      ? {
        id: tagValue,
        title: titleValue,
        label: questionValue,
        family: "rating",
        definition: {
          variant: "slider",
          range: { min: rangeStart, max: rangeEnd, step: stepValue },
          ui: { left_label: leftLabel, right_label: rightLabel },
        },
      }
      : ratingType === "emoji"
        ? {
          id: tagValue,
          title: titleValue,
          label: questionValue,
          family: "rating",
          definition: {
            variant: "emoji",
            emoji_list: getEmojiListType(),
            words: showEmojiWords,
            ui: { left_label: leftLabel, right_label: rightLabel },
          },
        }
        : {
          id: tagValue,
          title: titleValue,
          label: questionValue,
          family: "rating",
          definition: {
            variant: "star",
            stars: starCount,
            ui: { left_label: leftLabel, right_label: rightLabel },
          },
        };

  useImperativeHandle(ref, () => ({
    getData() {
      return ratingQuestionData;
    },
  }));

  useEffect(() => {
    onDataChange?.(ratingQuestionData);
  }, [titleValue, tagValue, questionValue, ratingType, rangeStart, rangeEnd, stepValue, leftLabel, rightLabel, starCount, emojiScaleType, showEmojiWords]);

  function alignToStep(value: number, min: number, max: number, step: number) {
    const safeStep = Math.max(1, Math.abs(step) || 1);
    const clamped = Math.min(max, Math.max(min, value));
    const stepped = min + Math.round((clamped - min) / safeStep) * safeStep;
    return Math.min(max, Math.max(min, stepped));
  }

  function updateRangeStart(nextValue: number) {
    const nextInteger = Math.min(1000, Math.max(-1000, Math.round(nextValue)));
    setRangeStart(nextInteger);
    if (nextInteger > rangeEnd) {
      setRangeEnd(nextInteger);
    }
  }

  function updateRangeEnd(nextValue: number) {
    const nextInteger = Math.min(1000, Math.max(-1000, Math.round(nextValue)));
    setRangeEnd(nextInteger);
    if (nextInteger < rangeStart) {
      setRangeStart(nextInteger);
    }
  }

  function updateStarCount(nextValue: number) {
    const nextCount = Math.min(MAX_STARS, Math.max(1, Math.round(nextValue) || 1));
    setStarCount(nextCount);
    setStarValue((current) => Math.min(nextCount, Math.max(0, current)));
  }

  const validSteps = getValidSteps(rangeStart, rangeEnd);
  const rangePreview =
    rangeStart === rangeEnd ? `${rangeStart}` : `${rangeStart} to ${rangeEnd}`;
  const safeStepValue = getNearestValidStep(Math.max(1, Math.abs(stepValue) || 1), validSteps);
  const currentStepIndex = validSteps.indexOf(safeStepValue);
  const normalizedSliderValue = alignToStep(sliderValue, rangeStart, rangeEnd, safeStepValue);
  const stepCount = Math.max(0, Math.floor((rangeEnd - rangeStart) / safeStepValue));
  const tickCount = Math.min(stepCount + 1, 101);
  const sliderRatio = rangeEnd === rangeStart
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
    if (stepValue !== safeStepValue) {
      setStepValue(safeStepValue);
    }
  }, [safeStepValue, stepValue]);

  useEffect(() => {
    setStarValue((current) => Math.min(starCount, Math.max(0, current)));
  }, [starCount]);

  function selectStarValue(nextValue: number) {
    setStarValue((current) => (current === nextValue ? 0 : nextValue));
  }

  function selectEmojiValue(nextValue: number) {
    setEmojiValue((current) => (current === nextValue ? 0 : nextValue));
  }

  function toggleEditMode() {
    setIsEditMode((current) => {
      const nextMode = !current;
      onEditModeChange?.(nextMode);
      return nextMode;
    });
  }

  const emojiScale = EMOJI_SCALES[emojiScaleType];
  const selectedEmoji = emojiScale.find((option) => option.value === emojiValue);
  const scaleSummary = ratingType === "stars"
    ? `0 to ${starCount}`
    : ratingType === "emoji"
      ? `0 to ${emojiScale.length}`
      : rangePreview;

  if (isCollapsed) {
    return <NodePillCollapsed family="Rating" tagValue={tagValue} title={titleValue} onExpand={() => { onExpand?.(); setIsEditMode(true); onEditModeChange?.(true); }} />;
  }

  return (
    <section className={`${nodePillShellClass} ${isEditMode ? nodePillShellEditClass : ""} rating-question`} aria-label="Rating question">
      <NodePillTopbar
        family="Rating"
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
          <NodePillFieldHead label="Rating">
            {isEditMode && (
              <NodePillCharCount
                label="Range"
                value={scaleSummary}
              />
            )}
          </NodePillFieldHead>

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
                    onChange={(event) => setRatingType(event.target.value as RatingType)}
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
                        onChange={(event) => setEmojiScaleType(event.target.value as EmojiScaleType)}
                      />
                      <div className={controlClass}>
                        <span className={controlLabelClass}>Words</span>
                        <Toggle
                          label="Show words"
                          checked={showEmojiWords}
                          disabled={!isEditMode}
                          onChange={setShowEmojiWords}
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
                              return;
                            }

                            updateRangeEnd(value);
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
                            setStepValue(validSteps[Math.max(0, currentStepIndex - 1)])
                          }
                          onIncrement={() =>
                            setStepValue(
                              validSteps[Math.min(validSteps.length - 1, currentStepIndex + 1)],
                            )
                          }
                          onChange={(value) =>
                            setStepValue(
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
                    onChange={(event) => setLeftLabel(event.target.value)}
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
                    onChange={(event) => setRightLabel(event.target.value)}
                    onKeyDown={blurOnEnter}
                  />
                </div>
              </>
            )}

            <div className={`${nodePillPreviewClass} rating-question__preview`}>
              <div className="text-[0.88rem] text-foreground">
                Current value: <strong>{ratingType === "stars"
                  ? `${starValue} / ${starCount}`
                  : ratingType === "emoji"
                    ? (selectedEmoji ? `${selectedEmoji.emoji}${showEmojiWords ? ` ${selectedEmoji.label}` : ""}` : "None")
                    : normalizedSliderValue}</strong>
              </div>
              <div className="flex justify-between gap-4 text-[0.95rem] text-muted-foreground [&>span:last-child]:text-right">
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
                        aria-checked={nextFullValue === starValue || nextHalfValue === starValue}
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
                  <span className="min-w-7 text-center text-[0.88rem] font-semibold text-foreground">{rangeStart}</span>
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
                          alignToStep(Number(event.target.value), rangeStart, rangeEnd, safeStepValue),
                        );
                      }}
                    />
                  </div>
                  <span className="min-w-7 text-center text-[0.88rem] font-semibold text-foreground">{rangeEnd}</span>
                </div>
              )}
              <div className="flex justify-between gap-4 text-[0.95rem] text-muted-foreground [&>span:last-child]:text-right">
                <span>{RATING_TYPE_OPTIONS.find((option) => option.value === ratingType)?.label}</span>
                <span>{ratingType === "stars" ? `${starCount} stars` : ratingType === "emoji" ? `${emojiScaleType === "sad" ? "Sad" : emojiScaleType === "angry" ? "Angry" : "Disgust"} to happy` : `Step ${stepValue}`}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
});
