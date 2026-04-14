import { useEffect, useState } from "react";
import "./RatingQuestion.css";

const QUESTION_MAX = 5000;
const MAX_STARS = 12;

type RatingType = "numeric-slider" | "emoji" | "stars";

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

export function RatingQuestion() {
  const [isEditMode, setIsEditMode] = useState(true);
  const [questionValue, setQuestionValue] = useState("");
  const [tagValue, setTagValue] = useState("question_id_1");
  const [ratingType, setRatingType] = useState<RatingType>("numeric-slider");
  const [rangeStart, setRangeStart] = useState(-5);
  const [rangeEnd, setRangeEnd] = useState(5);
  const [leftLabel, setLeftLabel] = useState("Strongly disagree");
  const [rightLabel, setRightLabel] = useState("Strongly agree");
  const [stepValue, setStepValue] = useState(1);
  const [sliderValue, setSliderValue] = useState(0);
  const [starCount, setStarCount] = useState(5);
  const [starValue, setStarValue] = useState(0);
  const [emojiValue, setEmojiValue] = useState(0);
  const [emojiScaleType, setEmojiScaleType] = useState<EmojiScaleType>("sad");
  const [showEmojiWords, setShowEmojiWords] = useState(true);

  function blurOnEnter(event: React.KeyboardEvent<HTMLElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      (event.currentTarget as HTMLElement).blur();
    }
  }

  function autoResizeTextarea(element: HTMLTextAreaElement) {
    element.style.height = "0px";
    const maxHeight = 600;
    const nextHeight = Math.min(element.scrollHeight, maxHeight);
    element.style.height = `${nextHeight}px`;
    element.style.overflowY = element.scrollHeight > maxHeight ? "auto" : "hidden";
  }

  function alignToStep(value: number, min: number, max: number, step: number) {
    const safeStep = Math.max(1, Math.abs(step) || 1);
    const clamped = Math.min(max, Math.max(min, value));
    const stepped = min + Math.round((clamped - min) / safeStep) * safeStep;
    return Math.min(max, Math.max(min, stepped));
  }

  function updateRangeStart(nextValue: number) {
    const nextInteger = Math.round(nextValue);
    setRangeStart(nextInteger);
    if (nextInteger > rangeEnd) {
      setRangeEnd(nextInteger);
    }
  }

  function updateRangeEnd(nextValue: number) {
    const nextInteger = Math.round(nextValue);
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

  const emojiScale = EMOJI_SCALES[emojiScaleType];
  const selectedEmoji = emojiScale.find((option) => option.value === emojiValue);
  const scaleSummary = ratingType === "stars"
    ? `0 to ${starCount}`
    : ratingType === "emoji"
      ? `0 to ${emojiScale.length}`
      : rangePreview;

  return (
    <section className={`blank-pill rating-question ${isEditMode ? "blank-pill--edit" : ""}`} aria-label="Rating question">
      <header className="blank-pill__topbar">
        <div className="blank-pill__topbar-left">
          <span className="blank-pill__family">Rating</span>
          <input
            className={`blank-pill__topbar-tag ${!isEditMode ? "blank-pill__topbar-tag--view" : ""}`}
            type="text"
            placeholder={isEditMode ? "question_id" : ""}
            value={tagValue}
            maxLength={40}
            size={Math.max(11, tagValue.length + 2)}
            readOnly={!isEditMode}
            onChange={(event) => setTagValue(event.target.value)}
            onKeyDown={blurOnEnter}
          />
        </div>

        <div className="blank-pill__actions">
          {isEditMode && (
            <>
              <button className="blank-pill__action blank-pill__action--danger" type="button">
                Delete
              </button>
              <button className="blank-pill__action" type="button">
                Settings
              </button>
            </>
          )}
          <button
            className={`blank-pill__action ${isEditMode ? "blank-pill__action--active" : ""}`}
            type="button"
            onClick={() => setIsEditMode((mode) => !mode)}
          >
            {isEditMode ? "Editing" : "Edit"}
          </button>
        </div>
      </header>

      <div className="blank-pill__body">
        <div className="blank-pill__field">
          <span className="blank-pill__label">Question</span>
          <div className="blank-pill__question-stack">
            <div className="blank-pill__question-field">
              <textarea
                className="blank-pill__question"
                placeholder="Type your question here"
                rows={3}
                maxLength={QUESTION_MAX}
                value={questionValue}
                readOnly={!isEditMode}
                onChange={(event) => setQuestionValue(event.target.value)}
                onInput={(event) => autoResizeTextarea(event.currentTarget)}
              />
            </div>
            {isEditMode && questionValue.length === QUESTION_MAX && (
              <span className="blank-pill__question-limit">
                Maximum {QUESTION_MAX} characters reached.
              </span>
            )}
          </div>
        </div>

        <div className="blank-pill__field">
          <span className="blank-pill__field-head">
            <span className="blank-pill__label">Scale</span>
            {isEditMode && (
              <span className="blank-pill__answer-char-count">
                <span className="blank-pill__answer-char-count-item">
                  <span className="blank-pill__answer-char-count-label">Range</span>
                  <span className="blank-pill__answer-char-count-value">{scaleSummary}</span>
                </span>
              </span>
            )}
          </span>

          <div className="rating-question__panel">
            {isEditMode && (
              <>
                <div className="rating-question__controls">
                  <label className="rating-question__control">
                    <span className="rating-question__control-label">Type</span>
                    <select
                      className="rating-question__select"
                      value={ratingType}
                      disabled={!isEditMode}
                      onChange={(event) => setRatingType(event.target.value as RatingType)}
                    >
                      {RATING_TYPE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  {ratingType === "stars" ? (
                    <label className="rating-question__control">
                      <span className="rating-question__control-label">Stars</span>
                      <div className="rating-question__stepper">
                        <button
                          className="rating-question__stepper-button"
                          type="button"
                          disabled={!isEditMode || starCount <= 1}
                          onClick={() => updateStarCount(starCount - 1)}
                        >
                          -
                        </button>
                        <input
                          className="rating-question__number-input rating-question__number-input--step"
                          type="text"
                          inputMode="numeric"
                          value={String(starCount)}
                          readOnly={!isEditMode}
                          onChange={(event) => updateStarCount(Number(event.target.value))}
                        />
                        <button
                          className="rating-question__stepper-button"
                          type="button"
                          disabled={!isEditMode || starCount >= MAX_STARS}
                          onClick={() => updateStarCount(starCount + 1)}
                        >
                          +
                        </button>
                      </div>
                    </label>
                  ) : ratingType === "emoji" ? (
                    <>
                      <div className="rating-question__control rating-question__control--span-2">
                        <span className="rating-question__control-label">Emoji list</span>
                        <select
                          className="rating-question__select"
                          value={emojiScaleType}
                          disabled={!isEditMode}
                          onChange={(event) => setEmojiScaleType(event.target.value as EmojiScaleType)}
                        >
                          <option value="sad">Sad to happy</option>
                          <option value="angry">Angry to happy</option>
                          <option value="disgust">Disgust to happy</option>
                        </select>
                      </div>
                      <label className="rating-question__control">
                        <span className="rating-question__control-label">Words</span>
                        <button
                          className={`rating-question__switch ${showEmojiWords ? "rating-question__switch--on" : ""}`}
                          type="button"
                          role="switch"
                          aria-checked={showEmojiWords}
                          disabled={!isEditMode}
                          onClick={() => setShowEmojiWords((current) => !current)}
                        >
                          <span className="rating-question__switch-track">
                            <span className="rating-question__switch-thumb" />
                          </span>
                          <span className="rating-question__switch-label">
                            {showEmojiWords ? "On" : "Off"}
                          </span>
                        </button>
                      </label>
                    </>
                  ) : (
                    <>
                      <label className="rating-question__control">
                        <span className="rating-question__control-label">From</span>
                        <input
                          className="rating-question__number-input"
                          type="number"
                          step={1}
                          value={rangeStart}
                          readOnly={!isEditMode}
                          onChange={(event) => updateRangeStart(Number(event.target.value))}
                        />
                      </label>

                      <label className="rating-question__control">
                        <span className="rating-question__control-label">To</span>
                        <input
                          className="rating-question__number-input"
                          type="number"
                          step={1}
                          value={rangeEnd}
                          readOnly={!isEditMode}
                          onChange={(event) => updateRangeEnd(Number(event.target.value))}
                        />
                      </label>

                      <label className="rating-question__control">
                        <span className="rating-question__control-label">Step</span>
                        <div className="rating-question__stepper">
                          <button
                            className="rating-question__stepper-button"
                            type="button"
                            disabled={!isEditMode || currentStepIndex <= 0}
                            onClick={() => setStepValue(validSteps[Math.max(0, currentStepIndex - 1)])}
                          >
                            -
                          </button>
                          <input
                            className="rating-question__number-input rating-question__number-input--step"
                            type="text"
                            inputMode="numeric"
                            value={String(stepValue)}
                            readOnly={!isEditMode}
                            onChange={(event) =>
                              setStepValue(
                                getNearestValidStep(Math.max(1, Number(event.target.value) || 1), validSteps),
                              )
                            }
                          />
                          <button
                            className="rating-question__stepper-button"
                            type="button"
                            disabled={!isEditMode || currentStepIndex >= validSteps.length - 1}
                            onClick={() =>
                              setStepValue(validSteps[Math.min(validSteps.length - 1, currentStepIndex + 1)])
                            }
                          >
                            +
                          </button>
                        </div>
                      </label>
                    </>
                  )}
                </div>

                <div className="rating-question__labels">
                  <label className="rating-question__control rating-question__control--wide">
                    <span className="rating-question__control-label">Left label</span>
                    <input
                      className="rating-question__text-input"
                      type="text"
                      placeholder="Low-end label"
                      value={leftLabel}
                      readOnly={!isEditMode}
                      onChange={(event) => setLeftLabel(event.target.value)}
                      onKeyDown={blurOnEnter}
                    />
                  </label>

                  <label className="rating-question__control rating-question__control--wide">
                    <span className="rating-question__control-label">Right label</span>
                    <input
                      className="rating-question__text-input"
                      type="text"
                      placeholder="High-end label"
                      value={rightLabel}
                      readOnly={!isEditMode}
                      onChange={(event) => setRightLabel(event.target.value)}
                      onKeyDown={blurOnEnter}
                    />
                  </label>
                </div>
              </>
            )}

            <div className="rating-question__preview">
              <div className="rating-question__preview-value">
                Current value: <strong>{ratingType === "stars"
                  ? `${starValue} / ${starCount}`
                  : ratingType === "emoji"
                    ? (selectedEmoji ? `${selectedEmoji.emoji}${showEmojiWords ? ` ${selectedEmoji.label}` : ""}` : "None")
                    : normalizedSliderValue}</strong>
              </div>
              <div className="rating-question__preview-labels">
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
                <div className="rating-question__preview-track">
                  <span className="rating-question__preview-end">{rangeStart}</span>
                  <div className="rating-question__preview-line">
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
                  <span className="rating-question__preview-end">{rangeEnd}</span>
                </div>
              )}
              <div className="rating-question__preview-meta">
                <span>{RATING_TYPE_OPTIONS.find((option) => option.value === ratingType)?.label}</span>
                <span>{ratingType === "stars" ? `${starCount} stars` : ratingType === "emoji" ? `${emojiScaleType === "sad" ? "Sad" : emojiScaleType === "angry" ? "Angry" : "Disgust"} to happy` : `Step ${stepValue}`}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
