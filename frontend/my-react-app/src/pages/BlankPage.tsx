import { useRef, useState } from "react";
import type { FieldQuestionHandle } from "../components/blank/FieldQuestion";
import type { MatchingQuestionHandle } from "../components/blank/MatchingQuestion";
import type { MultiChoiceQuestionHandle } from "../components/blank/MultiChoiceQuestion";
import type { RatingQuestionHandle } from "../components/blank/RatingQuestion";
import { FieldQuestion } from "../components/blank/FieldQuestion";
import { MatchingQuestion } from "../components/blank/MatchingQuestion";
import { MultiChoiceQuestion } from "../components/blank/MultiChoiceQuestion";
import { RatingQuestion } from "../components/blank/RatingQuestion";
import "./BlankPage.css";

type QuestionType = "multi-choice" | "matching" | "rating" | "field";

interface Question {
  id: string;
  type: QuestionType;
}

const QUESTION_TYPE_OPTIONS: Array<{ value: QuestionType; label: string }> = [
  { value: "multi-choice", label: "Multiple choice" },
  { value: "matching", label: "Matching" },
  { value: "rating", label: "Rating" },
  { value: "field", label: "Field" },
];

export function BlankPage() {
  const [questions, setQuestions] = useState<Question[]>([{ id: "q1", type: "field" }]);
  const [nextId, setNextId] = useState(2);
  const questionRefsMap = useRef<Map<string, FieldQuestionHandle | MatchingQuestionHandle | MultiChoiceQuestionHandle | RatingQuestionHandle>>(new Map());

  function addQuestion(type: QuestionType) {
    const newId = `q${nextId}`;
    setQuestions((current) => [...current, { id: newId, type }]);
    setNextId((current) => current + 1);
  }

  function removeQuestion(id: string) {
    setQuestions((current) => current.filter((q) => q.id !== id));
    questionRefsMap.current.delete(id);
  }

  function renderQuestion(question: Question) {
    const key = `question-${question.id}`;
    const handleRef = (ref: any) => {
      if (ref) {
        questionRefsMap.current.set(question.id, ref);
      }
    };

    switch (question.type) {
      case "multi-choice":
        return <MultiChoiceQuestion key={key} ref={handleRef} onDelete={() => removeQuestion(question.id)} />;
      case "matching":
        return <MatchingQuestion key={key} ref={handleRef} onDelete={() => removeQuestion(question.id)} />;
      case "rating":
        return <RatingQuestion key={key} ref={handleRef} onDelete={() => removeQuestion(question.id)} />;
      case "field":
        return <FieldQuestion key={key} ref={handleRef} onDelete={() => removeQuestion(question.id)} />;
    }
  }

  return (
    <section className="blank-page">
      <div className="blank-page__content">
        <div className="blank-page__questions-stack">
          {questions.map((question, index) => (
            <div key={question.id} className="blank-page__question-wrapper">
              <div className="blank-page__question-container">
                {renderQuestion(question)}
              </div>

              {index < questions.length - 1 && (
                <div className="blank-page__divider" />
              )}

              {index === questions.length - 1 && (
                <div className="blank-page__add-question">
                  <p className="blank-page__add-question-label">Add another question</p>
                  <div className="blank-page__add-question-buttons">
                    {QUESTION_TYPE_OPTIONS.map((option) => (
                      <button
                        key={option.value}
                        className="blank-page__add-question-btn"
                        type="button"
                        onClick={() => addQuestion(option.value)}
                      >
                        + {option.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
