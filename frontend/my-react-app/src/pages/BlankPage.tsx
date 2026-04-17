import { Fragment, type ReactNode, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { FieldQuestionHandle } from "../components/blank/FieldQuestion";
import type { MatchingQuestionHandle } from "../components/blank/MatchingQuestion";
import type { MultiChoiceQuestionHandle } from "../components/blank/MultiChoiceQuestion";
import type { RatingQuestionHandle } from "../components/blank/RatingQuestion";
import type { RulesQuestionHandle } from "../components/blank/RulesQuestion";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { FieldQuestion } from "../components/blank/FieldQuestion";
import { MatchingQuestion } from "../components/blank/MatchingQuestion";
import { MultiChoiceQuestion } from "../components/blank/MultiChoiceQuestion";
import { RatingQuestion } from "../components/blank/RatingQuestion";
import { RulesQuestion } from "../components/blank/RulesQuestion";
import "./BlankPage.css";

type QuestionType = "multi-choice" | "matching" | "rating" | "field" | "rules";

interface Question {
  id: string;
  type: QuestionType;
}

interface QuestionSummary {
  title: string;
  id: string;
}

const QUESTION_TYPE_OPTIONS: Array<{ value: QuestionType; label: string }> = [
  { value: "multi-choice", label: "Multiple choice" },
  { value: "matching", label: "Matching" },
  { value: "rating", label: "Rating" },
  { value: "field", label: "Field" },
  { value: "rules", label: "Rules" },
];

const SWAP_ANIMATION_MS = 280;

export function BlankPage() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [nextId, setNextId] = useState(1);
  const [editingQuestionIds, setEditingQuestionIds] = useState<string[]>([]);
  const [questionSummaries, setQuestionSummaries] = useState<Record<string, QuestionSummary>>({});
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState<"all" | QuestionType>("all");
  const questionRefsMap = useRef<Map<string, FieldQuestionHandle | MatchingQuestionHandle | MultiChoiceQuestionHandle | RatingQuestionHandle | RulesQuestionHandle>>(new Map());
  const questionWrapperNodeMap = useRef<Map<string, HTMLDivElement>>(new Map());
  const pendingMoveAnimation = useRef<{
    positions: Map<string, number>;
    movedId: string;
  } | null>(null);
  const newlyAddedQuestionId = useRef<string | null>(null);

  useLayoutEffect(() => {
    const pendingAnimation = pendingMoveAnimation.current;
    if (!pendingAnimation) return;

    const transitionMs = SWAP_ANIMATION_MS;
    const animatedNodes: HTMLDivElement[] = [];
    const movedQuestionNode = questionWrapperNodeMap.current.get(pendingAnimation.movedId);
    const previousMovedTop = pendingAnimation.positions.get(pendingAnimation.movedId);

    if (movedQuestionNode && previousMovedTop !== undefined) {
      const movedDeltaY = previousMovedTop - movedQuestionNode.getBoundingClientRect().top;
      window.scrollTo({
        top: window.scrollY - movedDeltaY,
      });
    }

    questions.forEach((question) => {
      const questionNode = questionWrapperNodeMap.current.get(question.id);
      const previousTop = pendingAnimation.positions.get(question.id);
      if (!questionNode || previousTop === undefined) return;

      const nextTop = questionNode.getBoundingClientRect().top;
      const deltaY = previousTop - nextTop;

      questionNode.style.position = "relative";
      questionNode.style.zIndex = question.id === pendingAnimation.movedId ? "3" : "1";

      const questionContainer = questionNode.querySelector<HTMLDivElement>(".blank-page__question-container");
      if (questionContainer && question.id === pendingAnimation.movedId) {
        questionContainer.style.boxShadow = "var(--shadow)";
      }

      if (!deltaY) {
        animatedNodes.push(questionNode);
        return;
      }

      animatedNodes.push(questionNode);
      questionNode.style.transition = "none";
      questionNode.style.transform = `translateY(${deltaY}px)`;
      questionNode.style.willChange = "transform";
    });

    if (animatedNodes.length === 0) {
      pendingMoveAnimation.current = null;
      return;
    }

    void document.body.offsetHeight;

    animatedNodes.forEach((questionNode) => {
      questionNode.style.transition = `transform ${transitionMs}ms cubic-bezier(0.2, 0.9, 0.2, 1)`;
      questionNode.style.transform = "translateY(0)";
    });

    const cleanupTimer = window.setTimeout(() => {
      animatedNodes.forEach((questionNode) => {
        questionNode.style.transition = "";
        questionNode.style.transform = "";
        questionNode.style.position = "";
        questionNode.style.zIndex = "";
        questionNode.style.willChange = "";
        const questionContainer = questionNode.querySelector<HTMLDivElement>(".blank-page__question-container");
        if (questionContainer) {
          questionContainer.style.boxShadow = "";
        }
      });

      pendingMoveAnimation.current = null;
    }, transitionMs + 32);

    return () => {
      window.clearTimeout(cleanupTimer);
    };
  }, [questions]);


  useEffect(() => {
    const addedId = newlyAddedQuestionId.current;
    if (!addedId) return;

    newlyAddedQuestionId.current = null;
    const node = questionWrapperNodeMap.current.get(addedId);
    if (node) {
      node.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [questions]);

  function addQuestion(type: QuestionType) {
    const newId = `q${nextId}`;
    newlyAddedQuestionId.current = newId;
    setQuestions((current) => [...current, { id: newId, type }]);
    setNextId((current) => current + 1);
    setEditingQuestionIds((current) =>
      current.includes(newId) ? current : [...current, newId],
    );
    setQuestionSummaries((current) => ({
      ...current,
      [newId]: { title: "", id: "question_id_1" },
    }));
  }

  function removeQuestion(id: string) {
    setQuestions((current) => {
      return current.filter((q) => q.id !== id);
    });
    setEditingQuestionIds((current) => current.filter((questionId) => questionId !== id));
    setQuestionSummaries((current) => {
      const nextSummaries = { ...current };
      delete nextSummaries[id];
      return nextSummaries;
    });
    questionRefsMap.current.delete(id);
    questionWrapperNodeMap.current.delete(id);
  }

  function moveQuestion(id: string, direction: "up" | "down") {
    setQuestions((current) => {
      const currentIndex = current.findIndex((question) => question.id === id);
      if (currentIndex === -1) return current;

      const targetIndex = direction === "up" ? currentIndex - 1 : currentIndex + 1;
      if (targetIndex < 0 || targetIndex >= current.length) return current;

      pendingMoveAnimation.current = {
        positions: new Map(
          current.map((question) => [
            question.id,
            questionWrapperNodeMap.current.get(question.id)?.getBoundingClientRect().top ?? 0,
          ]),
        ),
        movedId: id,
      };

      const nextQuestions = [...current];
      const [movedQuestion] = nextQuestions.splice(currentIndex, 1);
      nextQuestions.splice(targetIndex, 0, movedQuestion);
      return nextQuestions;
    });
  }

  function renderQuestion(question: Question) {
    const key = `question-${question.id}`;
    const handleRef = (ref: any) => {
      if (ref) {
        questionRefsMap.current.set(question.id, ref);
      }
    };
    const handleEditModeChange = (isEditMode: boolean) => {
      setEditingQuestionIds((current) => {
        if (isEditMode) {
          return current.includes(question.id) ? current : [...current, question.id];
        }

        return current.filter((questionId) => questionId !== question.id);
      });
    };
    const handleDataChange = (summary: QuestionSummary) => {
      setQuestionSummaries((current) => {
        const existingSummary = current[question.id];
        if (
          existingSummary &&
          existingSummary.title === summary.title &&
          existingSummary.id === summary.id
        ) {
          return current;
        }

        return {
          ...current,
          [question.id]: summary,
        };
      });
    };

    switch (question.type) {
      case "multi-choice":
        return <MultiChoiceQuestion key={key} ref={handleRef} onDelete={() => removeQuestion(question.id)} onEditModeChange={handleEditModeChange} onDataChange={handleDataChange} />;
      case "matching":
        return <MatchingQuestion key={key} ref={handleRef} onDelete={() => removeQuestion(question.id)} onEditModeChange={handleEditModeChange} onDataChange={handleDataChange} />;
      case "rating":
        return <RatingQuestion key={key} ref={handleRef} onDelete={() => removeQuestion(question.id)} onEditModeChange={handleEditModeChange} onDataChange={handleDataChange} />;
      case "field":
        return <FieldQuestion key={key} ref={handleRef} onDelete={() => removeQuestion(question.id)} onEditModeChange={handleEditModeChange} onDataChange={handleDataChange} />;
      case "rules":
        return <RulesQuestion key={key} ref={handleRef} onDelete={() => removeQuestion(question.id)} onEditModeChange={handleEditModeChange} onDataChange={handleDataChange} />;
    }
  }

  const addQuestionCard = (
    <div className="blank-page__add-question">
      <div className="blank-page__add-question-head">
        <Badge variant="accent" size="sm">Build</Badge>
        <p className="blank-page__add-question-label">Add another question</p>
        <p className="blank-page__add-question-copy">
          Choose the next response format to keep building the flow.
        </p>
      </div>
      <div className="blank-page__add-question-buttons">
        {QUESTION_TYPE_OPTIONS.map((option) => (
          <Button
            key={option.value}
            className="blank-page__add-question-btn"
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => addQuestion(option.value)}
          >
            <span aria-hidden="true">+</span>
            {option.label}
          </Button>
        ))}
      </div>
    </div>
  );

  const isQuestionExpanded = (question: Question) => {
    const questionSummary = questionSummaries[question.id] ?? { title: "", id: "question_id_1" };
    const normalizedSearch = searchQuery.trim().toLowerCase();
    const title = questionSummary.title.trim() || "Untitled question";
    const id = questionSummary.id.trim() || "question_id_1";
    const matchesFilter = filterType === "all" || question.type === filterType;
    const matchesSearch =
      normalizedSearch === "" ||
      `${title} ${id}`.toLowerCase().includes(normalizedSearch);

    return matchesFilter && matchesSearch;
  };

  return (
    <section className="blank-page">
      <div className="blank-page__toolbar">
        <div className="blank-page__toolbar-header">
          <h4 className="blank-page__toolbar-title">Search</h4>
          <Input
            className="blank-page__toolbar-search-input"
            placeholder="Search by title or ID"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
          />
          <Select
            className="blank-page__toolbar-filter"
            value={filterType}
            options={[
              { value: "all", label: "All question types" },
              ...QUESTION_TYPE_OPTIONS,
            ]}
            onChange={(event) => setFilterType(event.target.value as "all" | QuestionType)}
          />
        </div>
      </div>
      <div className="blank-page__content">
        <div className="blank-page__questions-stack">
          {questions.map((question, index) => {
            const nextQuestion = questions[index + 1];
            const shouldShowDivider =
              index < questions.length - 1 &&
              (isQuestionExpanded(question) || (nextQuestion ? isQuestionExpanded(nextQuestion) : false));

            return (
            <Fragment key={question.id}>
              <QuestionRow
                question={question}
                index={index}
                isLast={index === questions.length - 1}
                questionSummary={questionSummaries[question.id] ?? { title: "", id: "question_id_1" }}
                isEditing={editingQuestionIds.includes(question.id)}
                filterType={filterType}
                searchQuery={searchQuery}
                onMoveQuestion={moveQuestion}
                onSetWrapperNode={(node) => {
                  if (node) {
                    questionWrapperNodeMap.current.set(question.id, node);
                  } else {
                    questionWrapperNodeMap.current.delete(question.id);
                  }
                }}
              >
                {renderQuestion(question)}
              </QuestionRow>

              {shouldShowDivider && (
                <div className="blank-page__divider" />
              )}

              {index === questions.length - 1 && (
                <>
                  <div className="blank-page__divider blank-page__divider--section" />
                  {addQuestionCard}
                </>
              )}
            </Fragment>
          )})}
          {questions.length === 0 && addQuestionCard}
        </div>
      </div>
    </section>
  );
}

function QuestionRow({
  question,
  index,
  isLast,
  questionSummary,
  isEditing,
  filterType,
  searchQuery,
  onMoveQuestion,
  onSetWrapperNode,
  children,
}: {
  question: Question;
  index: number;
  isLast: boolean;
  questionSummary: QuestionSummary;
  isEditing: boolean;
  filterType: "all" | QuestionType;
  searchQuery: string;
  onMoveQuestion: (id: string, direction: "up" | "down") => void;
  onSetWrapperNode: (node: HTMLDivElement | null) => void;
  children: ReactNode;
}) {
  const normalizedSearch = searchQuery.trim().toLowerCase();
  const title = questionSummary.title.trim() || "Untitled question";
  const id = questionSummary.id.trim() || "question_id_1";
  const matchesFilter = filterType === "all" || question.type === filterType;
  const matchesSearch =
    normalizedSearch === "" ||
    `${title} ${id}`.toLowerCase().includes(normalizedSearch);
  const isExpanded = matchesFilter && matchesSearch;

  return (
    <div
      ref={onSetWrapperNode}
      className={`blank-page__question-wrapper ${
        isExpanded ? "" : "blank-page__question-wrapper--collapsed"
      }`}
    >
      <div className="blank-page__question-row">
        <div className="blank-page__question-container">
          <div className={isExpanded ? "" : "blank-page__question-content--hidden"}>
            {children}
          </div>
          {!isExpanded && (
            <div className="blank-page__question-summary">
              <p className="blank-page__question-summary-title">{title}</p>
              <p className="blank-page__question-summary-id">{id}</p>
            </div>
          )}
        </div>

        {isExpanded && isEditing && (
          <div className="blank-page__question-move-controls" aria-label="Move question">
            <Button
              className="blank-page__question-move-btn"
              type="button"
              variant="quiet"
              size="xs"
              disabled={index === 0}
              aria-label="Move question up"
              onClick={() => onMoveQuestion(question.id, "up")}
            >
              ↑
            </Button>
            <Button
              className="blank-page__question-move-btn"
              type="button"
              variant="quiet"
              size="xs"
              disabled={isLast}
              aria-label="Move question down"
              onClick={() => onMoveQuestion(question.id, "down")}
            >
              ↓
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
