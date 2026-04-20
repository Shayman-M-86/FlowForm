import type { EmojiListType, RatingContent } from "../node/questionTypes";
import "../node/RatingQuestion.css";

interface RatingFormFillerProps {
  question: RatingContent;
  value: number | null;
  onChange: (nextValue: number | null) => void;
}

const EMOJI_SETS: Record<EmojiListType, Array<{ symbol: string; label: string }>> = {
  sad_to_happy: [
    { symbol: "😢", label: "Sad" },
    { symbol: "🙁", label: "Low" },
    { symbol: "😐", label: "Neutral" },
    { symbol: "🙂", label: "Good" },
    { symbol: "😄", label: "Happy" },
  ],
  angry_to_happy: [
    { symbol: "😠", label: "Angry" },
    { symbol: "😒", label: "Tense" },
    { symbol: "😐", label: "Neutral" },
    { symbol: "🙂", label: "Calm" },
    { symbol: "😄", label: "Happy" },
  ],
  disgust_to_happy: [
    { symbol: "🤢", label: "Disgusted" },
    { symbol: "😕", label: "Uneasy" },
    { symbol: "😐", label: "Neutral" },
    { symbol: "🙂", label: "Pleased" },
    { symbol: "😄", label: "Happy" },
  ],
};

export function RatingFormFiller({
  question,
  value,
  onChange,
}: RatingFormFillerProps) {
  switch (question.definition.variant) {
    case "slider": {
      const sliderDefinition = question.definition;
      const validSteps = getValidSteps(sliderDefinition.range.min, sliderDefinition.range.max);
      const safeStep = getNearestValidStep(sliderDefinition.range.step, validSteps);
      const resolvedValue = typeof value === "number"
        ? alignToStep(value, sliderDefinition.range.min, sliderDefinition.range.max, safeStep)
        : sliderDefinition.range.min;
      const stepCount = Math.max(0, Math.floor((sliderDefinition.range.max - sliderDefinition.range.min) / safeStep));
      const tickCount = Math.min(stepCount + 1, 101);
      const tickValues = Array.from({ length: tickCount }, (_, index) => {
        if (tickCount === 1) return sliderDefinition.range.min;
        if (index === tickCount - 1) return sliderDefinition.range.max;
        return sliderDefinition.range.min + index * safeStep;
      });

      return (
        <div className="form-filler-question__body">
          <div className="rating-question__preview">
            <div className="rating-question__preview-track">
              <span className="rating-question__control-label">{sliderDefinition.ui.left_label || "Low"}</span>
              <div className="rating-question__preview-line">
                <div className="rating-question__slider-track" />
                <div className="rating-question__slider-ticks" aria-hidden="true">
                  {tickValues.map((tickValue) => (
                    <span key={tickValue} className="rating-question__slider-tick" />
                  ))}
                </div>
                <input
                  className="rating-question__slider"
                  type="range"
                  min={sliderDefinition.range.min}
                  max={sliderDefinition.range.max}
                  step={safeStep}
                  value={resolvedValue}
                  onChange={(event) => onChange(Number(event.target.value))}
                />
              </div>
              <span className="rating-question__control-label">{sliderDefinition.ui.right_label || "High"}</span>
            </div>
            <div className="form-filler-rating__value-pill">
              {typeof value === "number" ? `Selected value: ${resolvedValue}` : "Move the slider to choose a value."}
            </div>
          </div>
        </div>
      );
    }
    case "emoji": {
      const emojiDefinition = question.definition;
      return (
        <div className="form-filler-question__body">
          <div className="rating-question__preview">
            <div className={`rating-question__emoji-list ${emojiDefinition.words ? "" : "rating-question__emoji-list--icons-only"}`} role="radiogroup" aria-label={question.title}>
              {EMOJI_SETS[emojiDefinition.emoji_list].map((emoji, index) => {
                const score = index + 1;
                const isSelected = value === score;

                return (
                  <button
                    key={`${emoji.symbol}-${score}`}
                    type="button"
                    className={`rating-question__emoji-option ${isSelected ? "rating-question__emoji-option--active" : ""}`}
                    onClick={() => onChange(score)}
                  >
                    <span className="rating-question__emoji-glyph" aria-hidden="true">{emoji.symbol}</span>
                    {emojiDefinition.words && <span className="rating-question__emoji-label">{emoji.label}</span>}
                  </button>
                );
              })}
            </div>
            <div className="form-filler-rating__scale-labels">
              <span>{emojiDefinition.ui.left_label || "Low"}</span>
              <span>{emojiDefinition.ui.right_label || "High"}</span>
            </div>
          </div>
        </div>
      );
    }
    case "star": {
      const starDefinition = question.definition;
      function selectStarValue(nextValue: number) {
        onChange(value === nextValue ? null : nextValue);
      }

      return (
        <div className="form-filler-question__body">
          <div className="rating-question__preview">
            <div
              className="rating-question__stars"
              role="radiogroup"
              aria-label={question.title}
              style={{ "--rating-star-count": starDefinition.stars } as React.CSSProperties}
            >
              {Array.from({ length: starDefinition.stars }, (_, index) => {
                const nextFullValue = index + 1;
                const nextHalfValue = index + 0.5;
                const fillLevel = Math.max(0, Math.min(1, (value ?? 0) - index));

                return (
                  <div
                    key={nextFullValue}
                    className="rating-question__star"
                    role="radio"
                    aria-checked={nextFullValue === value || nextHalfValue === value}
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
                      onClick={() => selectStarValue(nextHalfValue)}
                    />
                    <button
                      className="rating-question__star-hit rating-question__star-hit--right"
                      type="button"
                      aria-label={`${nextFullValue} stars`}
                      onClick={() => selectStarValue(nextFullValue)}
                    />
                  </div>
                );
              })}
            </div>
            <div className="form-filler-rating__scale-labels">
              <span>{starDefinition.ui.left_label || "Low"}</span>
              <span>{starDefinition.ui.right_label || "High"}</span>
            </div>
          </div>
        </div>
      );
    }
    default:
      return null;
  }
}

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

function alignToStep(value: number, min: number, max: number, step: number) {
  const safeStep = Math.max(1, Math.abs(step) || 1);
  const clamped = Math.min(max, Math.max(min, value));
  const stepped = min + Math.round((clamped - min) / safeStep) * safeStep;
  return Math.min(max, Math.max(min, stepped));
}
