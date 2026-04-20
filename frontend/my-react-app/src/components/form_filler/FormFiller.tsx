import { useEffect, useRef, useState } from "react";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { FieldFormFiller } from "./FieldFormFiller";
import { MatchingFormFiller } from "./MatchingFormFiller";
import { MultiChoiceFormFiller } from "./MultiChoiceFormFiller";
import { RatingFormFiller } from "./RatingFormFiller";
import {
  deriveSurveyProgress,
  prepareSurvey,
  validateQuestionAnswer,
  type AnswerMap,
  type PreparedSurvey,
  type QuestionAnswer,
} from "./formFillerRuntime";
import type { QuestionContent, SurveyNode } from "../node/questionTypes";
import "./formFiller.css";

export interface FormFillerResult {
  status: "submitted" | "discarded";
  answers: Record<string, QuestionAnswer | null>;
  committedQuestionIds: string[];
}

interface FormFillerProps {
  survey: SurveyNode[];
  title?: string;
  description?: string;
  emptyTitle?: string;
  emptyMessage?: string;
  exitLabel?: string;
  onExit?: () => void;
  onComplete?: (result: FormFillerResult) => void;
  showAnswerSummary?: boolean;
  stackSidebar?: boolean;
}

export function FormFiller({
  survey,
  title,
  description = "Complete each step to continue.",
  emptyTitle = "No survey is available",
  emptyMessage = "There are no survey steps to render.",
  exitLabel = "Close",
  onExit,
  onComplete,
  showAnswerSummary = false,
  stackSidebar = false,
}: FormFillerProps) {
  const [answers, setAnswers] = useState<AnswerMap>({});
  const [committedQuestionIds, setCommittedQuestionIds] = useState<string[]>([]);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const lastReportedCompletionKey = useRef<string | null>(null);

  useEffect(() => {
    setAnswers({});
    setCommittedQuestionIds([]);
    setValidationMessage(null);
    lastReportedCompletionKey.current = null;
  }, [survey]);

  const preparedSurvey = prepareSurvey(survey);
  const progress = deriveSurveyProgress(preparedSurvey, answers, committedQuestionIds);
  const currentQuestion = progress.currentQuestionId
    ? preparedSurvey.questionById.get(progress.currentQuestionId) ?? null
    : null;
  const currentQuestionState = currentQuestion
    ? progress.questionStateMap[currentQuestion.id]
    : undefined;
  const projectedProgress = currentQuestion
    ? deriveSurveyProgress(preparedSurvey, answers, [...progress.effectiveCommittedIds, currentQuestion.id])
    : null;
  const answerSummary = buildAnswerSummary(preparedSurvey, answers, progress.effectiveCommittedIds);
  const completionResult = progress.status === "active"
    ? null
    : {
      status: progress.status,
      answers: answerSummary,
      committedQuestionIds: progress.effectiveCommittedIds,
    };

  useEffect(() => {
    if (!completionResult) {
      lastReportedCompletionKey.current = null;
      return;
    }

    const completionKey = `${completionResult.status}:${completionResult.committedQuestionIds.join("|")}`;
    if (lastReportedCompletionKey.current === completionKey) return;

    lastReportedCompletionKey.current = completionKey;
    onComplete?.(completionResult);
  }, [completionResult, onComplete]);

  function handleAnswerChange(questionId: string, nextValue: QuestionAnswer) {
    setAnswers((current) => ({
      ...current,
      [questionId]: nextValue,
    }));
    setValidationMessage(null);
  }

  function handleContinue() {
    if (!currentQuestion) return;

    const error = validateQuestionAnswer(
      currentQuestion,
      answers[currentQuestion.id],
      currentQuestionState?.required ?? true,
    );

    if (error) {
      setValidationMessage(error);
      return;
    }

    setValidationMessage(null);
    setCommittedQuestionIds([...progress.effectiveCommittedIds, currentQuestion.id]);
  }

  function handleBack() {
    setCommittedQuestionIds(progress.effectiveCommittedIds.slice(0, -1));
    setValidationMessage(null);
  }

  function handleRestart() {
    setAnswers({});
    setCommittedQuestionIds([]);
    setValidationMessage(null);
    lastReportedCompletionKey.current = null;
  }

  if (survey.length === 0) {
    return (
      <section className="form-filler-page">
        <div className="form-filler form-filler--single-column">
          <div className="form-filler__empty-state">
            {title && <Badge variant="accent" size="sm">{title}</Badge>}
            <h1 className="form-filler__completion-title">{emptyTitle}</h1>
            <p className="form-filler__completion-copy">{emptyMessage}</p>
            {onExit && (
              <div className="form-filler__completion-actions">
                <Button type="button" variant="primary" onClick={onExit}>
                  {exitLabel}
                </Button>
              </div>
            )}
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="form-filler-page">
      <div
        className={`form-filler ${showAnswerSummary ? "" : "form-filler--single-column"} ${stackSidebar ? "form-filler--stacked" : ""}`}
      >
        <div className="form-filler__panel">
          {progress.status === "active" && currentQuestion ? (
            <>
              <header className="form-filler__panel-head">
                <div>
                  {currentQuestion.title.trim() !== "" && (
                    <h1 className="form-filler__title">{currentQuestion.title}</h1>
                  )}
                </div>
                <span className="form-filler__requirement">
                  {(currentQuestionState?.required ?? true) ? "Required" : "Optional"}
                </span>
              </header>

              <div className="form-filler__prompt-card">
                <div className="form-filler__prompt-scroll">
                  <p className="form-filler__prompt">
                    {currentQuestion.label || description}
                  </p>
                </div>
              </div>

              {renderQuestionInput(currentQuestion, answers[currentQuestion.id], handleAnswerChange)}

              {validationMessage && (
                <div className="form-filler__error" role="alert">
                  {validationMessage}
                </div>
              )}

              <div className="form-filler__actions">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={handleBack}
                  disabled={progress.effectiveCommittedIds.length === 0}
                >
                  Back
                </Button>
                <Button type="button" variant="primary" onClick={handleContinue}>
                  {projectedProgress?.status === "submitted"
                    ? "Submit"
                    : projectedProgress?.status === "discarded"
                      ? "Finish"
                      : "Continue"}
                </Button>
                {onExit && (
                  <Button type="button" variant="quiet" onClick={onExit}>
                    {exitLabel}
                  </Button>
                )}
              </div>
            </>
          ) : (
            <div className="form-filler__completion">
              <Badge variant="accent" size="sm">
                {completionResult?.status === "discarded" ? "Closed" : "Complete"}
              </Badge>
              <h1 className="form-filler__completion-title">
                {completionResult?.status === "discarded" ? "This response flow ended" : "Survey complete"}
              </h1>
              <p className="form-filler__completion-copy">
                {completionResult?.status === "discarded"
                  ? "A rule ended the survey before submission."
                  : "All visible survey steps have been completed."}
              </p>
              {showAnswerSummary && (
                <pre className="form-filler__json">{JSON.stringify(answerSummary, null, 2)}</pre>
              )}
              <div className="form-filler__completion-actions">
                <Button type="button" variant="primary" onClick={handleRestart}>
                  Start over
                </Button>
                {onExit && (
                  <Button type="button" variant="secondary" onClick={onExit}>
                    {exitLabel}
                  </Button>
                )}
              </div>
            </div>
          )}
        </div>

        {showAnswerSummary && (
          <aside className="form-filler__sidebar">
            <div className="form-filler__sidebar-card">
              <p className="form-filler__eyebrow">Progress</p>
              <h2 className="form-filler__sidebar-title">Survey state</h2>
              <ul className="form-filler__sidebar-list">
                <li>{preparedSurvey.questionNodes.length} question nodes</li>
                <li>{preparedSurvey.nodes.length - preparedSurvey.questionNodes.length} rule nodes</li>
                <li>{progress.effectiveCommittedIds.length} completed step{progress.effectiveCommittedIds.length === 1 ? "" : "s"}</li>
              </ul>
            </div>

            <div className="form-filler__sidebar-card">
              <h2 className="form-filler__sidebar-title">Answers</h2>
              <pre className="form-filler__json">{JSON.stringify(answerSummary, null, 2)}</pre>
            </div>
          </aside>
        )}
      </div>
    </section>
  );
}

function buildAnswerSummary(
  preparedSurvey: PreparedSurvey,
  answers: AnswerMap,
  committedQuestionIds: string[],
) {
  return Object.fromEntries(
    committedQuestionIds
      .filter((questionId) => preparedSurvey.questionById.has(questionId))
      .map((questionId) => [questionId, answers[questionId] ?? null]),
  );
}

function renderQuestionInput(
  question: QuestionContent,
  answer: QuestionAnswer | undefined,
  onChange: (questionId: string, nextValue: QuestionAnswer) => void,
) {
  switch (question.family) {
    case "choice":
      return (
        <MultiChoiceFormFiller
          question={question}
          value={Array.isArray(answer) ? answer.filter((value): value is string => typeof value === "string") : []}
          onChange={(nextValue) => onChange(question.id, nextValue)}
        />
      );
    case "matching":
      return (
        <MatchingFormFiller
          question={question}
          value={toRecord(answer)}
          onChange={(nextValue) => onChange(question.id, nextValue)}
        />
      );
    case "rating":
      return (
        <RatingFormFiller
          question={question}
          value={typeof answer === "number" ? answer : null}
          onChange={(nextValue) => onChange(question.id, nextValue)}
        />
      );
    case "field":
      return (
        <FieldFormFiller
          question={question}
          value={typeof answer === "string" ? answer : ""}
          onChange={(nextValue) => onChange(question.id, nextValue)}
        />
      );
    default:
      return null;
  }
}

function toRecord(answer: QuestionAnswer | undefined): Record<string, string> {
  if (!answer || typeof answer !== "object" || Array.isArray(answer)) {
    return {};
  }

  return Object.fromEntries(
    Object.entries(answer).filter((entry): entry is [string, string] => typeof entry[1] === "string"),
  );
}
