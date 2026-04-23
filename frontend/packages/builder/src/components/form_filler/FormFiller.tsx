import { useEffect, useRef, useState } from "react";

import { Badge, Button } from "@flowform/ui";
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

const panelClass = [
  "flex w-full min-w-0 flex-col gap-7 rounded-3xl border border-border bg-card p-7",
  "shadow-md backdrop-blur-md",
  "max-sm:rounded-2xl max-sm:p-5.5",
].join(" ");

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
  const isContinueDisabled = currentQuestion
    ? Boolean(validateQuestionAnswer(currentQuestion, answers[currentQuestion.id], currentQuestionState?.required ?? true))
    : false;
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
      <section className="box-border min-h-full px-8 py-9 max-sm:min-h-screen max-sm:px-4.5 max-sm:py-6">
        <div className="mx-auto w-full max-w-[760px]">
          <div className={panelClass}>
            {title && <Badge variant="accent" size="sm">{title}</Badge>}
            <h1 className="m-0 text-[clamp(1.7rem,4vw,2.4rem)] text-foreground">{emptyTitle}</h1>
            <p className="m-0 leading-relaxed text-muted-foreground">{emptyMessage}</p>
            {onExit && (
              <div className="flex flex-wrap gap-3">
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

  const isSingleColumn = !showAnswerSummary || stackSidebar;

  return (
    <section className="box-border min-h-full px-8 py-9 max-sm:min-h-screen max-sm:flex max-sm:items-center max-sm:justify-center max-sm:px-4.5 max-sm:py-6">
      <div
        className={[
          "mx-auto w-full",
          isSingleColumn
            ? "flex max-w-[1120px] justify-center"
            : "grid max-w-[1360px] grid-cols-[minmax(0,1fr)_320px] items-start gap-6 max-[920px]:grid-cols-1",
        ].join(" ")}
      >
        <div className={panelClass}>
          {progress.status === "active" && currentQuestion ? (
            <>
              <header className="flex items-start justify-between max-sm:flex-col">
                <div>
                  {currentQuestion.title.trim() !== "" && (
                    <h1 className="m-0 text-[clamp(1.35rem,3vw,1.9rem)] leading-[1.15] text-foreground">
                      {currentQuestion.title}
                    </h1>
                  )}
                </div>
                <span className="inline-flex min-w-[108px] items-center justify-center rounded-full bg-muted px-3.5 py-2.5 text-[0.85rem] font-semibold text-foreground">
                  {(currentQuestionState?.required ?? true) ? "Required" : "Optional"}
                </span>
              </header>

              <div className="overflow-hidden rounded-2xl border border-border bg-muted/20">
                <div className="max-h-[420px] overflow-y-auto px-5.5 py-5">
                  <p className="m-0 whitespace-pre-wrap break-words text-[clamp(1.15rem,2.4vw,1.45rem)] font-semibold leading-[1.55] text-foreground">
                    {currentQuestion.label || description}
                  </p>
                </div>
              </div>

              {renderQuestionInput(currentQuestion, answers[currentQuestion.id], handleAnswerChange)}

              {validationMessage && (
                <div
                  className="rounded-2xl border border-destructive/40 bg-destructive/10 px-4 py-3.5 text-destructive"
                  role="alert"
                >
                  {validationMessage}
                </div>
              )}

              <div className="flex flex-wrap gap-3">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={handleBack}
                  disabled={progress.effectiveCommittedIds.length === 0}
                >
                  Back
                </Button>
                <Button type="button" variant="primary" onClick={handleContinue} disabled={isContinueDisabled}>
                  {projectedProgress?.status === "submitted"
                    ? "Submit"
                    : projectedProgress?.status === "discarded"
                      ? "Finish"
                      : "Continue"}
                </Button>
                {onExit && (
                  <Button type="button" variant="secondary" onClick={onExit}>
                    {exitLabel}
                  </Button>
                )}
              </div>
            </>
          ) : (
            <div className="flex flex-col gap-4.5">
              <Badge variant="accent" size="sm">
                {completionResult?.status === "discarded" ? "Closed" : "Complete"}
              </Badge>
              <h1 className="m-0 text-[clamp(1.7rem,4vw,2.4rem)] text-foreground">
                {completionResult?.status === "discarded" ? "This response flow ended" : "Survey complete"}
              </h1>
              <p className="m-0 leading-relaxed text-muted-foreground">
                {completionResult?.status === "discarded"
                  ? "A rule ended the survey before submission."
                  : "All visible survey steps have been completed."}
              </p>
              {showAnswerSummary && (
                <pre className="m-0 overflow-auto rounded-2xl bg-muted p-4 font-mono text-[0.82rem] leading-[1.55] text-foreground">
                  {JSON.stringify(answerSummary, null, 2)}
                </pre>
              )}
              <div className="flex flex-wrap gap-3">
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
