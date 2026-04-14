import { useState } from "react";
import { FieldQuestion } from "../components/blank/FieldQuestion";
import { MatchingQuestion } from "../components/blank/MatchingQuestion";
import { MultiChoiceQuestion } from "../components/blank/MultiChoiceQuestion";
import { RatingQuestion } from "../components/blank/RatingQuestion";
import "./BlankPage.css";

type QuestionType = "multi-choice" | "matching" | "rating" | "field";

const QUESTION_TYPE_OPTIONS: Array<{ value: QuestionType; label: string }> = [
  { value: "multi-choice", label: "Multiple choice" },
  { value: "matching", label: "Matching" },
  { value: "rating", label: "Rating" },
  { value: "field", label: "Field" },
];

export function BlankPage() {
  const [questionType, setQuestionType] = useState<QuestionType>("field");

  const card = questionType === "multi-choice"
    ? <MultiChoiceQuestion />
    : questionType === "matching"
      ? <MatchingQuestion />
      : questionType === "rating"
        ? <RatingQuestion />
        : <FieldQuestion />;

  return (
    <section className="blank-page">
      <div className="blank-page__content">
        <div className="blank-page__toggle-group" role="tablist" aria-label="Question type">
          {QUESTION_TYPE_OPTIONS.map((option) => (
            <button
              key={option.value}
              className={`blank-page__toggle ${questionType === option.value ? "blank-page__toggle--active" : ""}`}
              type="button"
              role="tab"
              aria-selected={questionType === option.value}
              onClick={() => setQuestionType(option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>
        <div className="blank-page__card">{card}</div>
      </div>
    </section>
  );
}
