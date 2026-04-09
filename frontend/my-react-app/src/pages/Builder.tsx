import { useState } from "react";
import { QuestionCard, type Question } from "../components/QuestionCard";
import "./Builder.css";

export function BuilderPage() {
  const [questions, setQuestions] = useState<Question[]>([
    { id: 1, title: "What is your favourite colour?", logic: null },
  ]);
  function handleDelete(id: number) {
    setQuestions(q => q.filter(x => x.id !== id));
  }

  return (
    <div className="builder-page">
      <div className="builder-page__inner">
        {questions.map((q, i) => (
          <QuestionCard
            key={q.id}
            question={q}
            index={i + 1}
            onEdit={() => {}}
            onDelete={handleDelete}
            onEditLogic={() => {}}
          />
        ))}
      </div>
    </div>
  );
}
