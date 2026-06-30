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
import type { QuestionNode, SurveyNode } from "../node/questionTypes";

export interface SubmissionAnswer {
  question_key: string;
  answer: QuestionAnswer | null;
}

export interface FormFillerResult {
  status: "submitted" | "discarded";
  answers: SubmissionAnswer[];
  committedQuestionIds: string[];
}

interface FormFillerProps {
  survey: SurveyNode[];
  title?: string;
  description?: string;
  emptyTitle?: string;
  emptyMessage?: string;
  exitLabel?: string;
  submitLabel?: string;
  onExit?: () => void;
  onComplete?: (result: FormFillerResult) => void;
  onAnswerCommit?: (questionKey: string, answer: QuestionAnswer) => void;
  showAnswerSummary?: boolean;
  stackSidebar?: boolean;
  confirmSubmit?: boolean;
}

interface AnswerReviewItem {
  questionKey: string;
  title: string;
  prompt: string;
  answer: string | string[];
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
  submitLabel = "Submit",
  onExit,
  onComplete,
  onAnswerCommit,
  showAnswerSummary = false,
  stackSidebar = false,
  confirmSubmit = false,
}: FormFillerProps) {
  const [answers, setAnswers] = useState<AnswerMap>({});
  const [committedQuestionIds, setCommittedQuestionIds] = useState<string[]>([]);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const lastReportedCompletionKey = useRef<string | null>(null);
  const [userConfirmedSubmit, setUserConfirmedSubmit] = useState(false);

  useEffect(() => {
    setAnswers({});
    setCommittedQuestionIds([]);
    setValidationMessage(null);
    lastReportedCompletionKey.current = null;
  }, [survey]);

  const preparedSurvey = prepareSurvey(survey);
  const progress = deriveSurveyProgress(preparedSurvey, answers, committedQuestionIds);
  const currentNode = progress.currentQuestionId
    ? preparedSurvey.questionById.get(progress.currentQuestionId) ?? null
    : null;
  const currentQuestion = currentNode?.content ?? null;
  const currentQuestionState = currentNode
    ? progress.questionStateMap[currentNode.node_key]
    : undefined;
  const projectedProgress = currentNode
    ? deriveSurveyProgress(preparedSurvey, answers, [...progress.effectiveCommittedIds, currentNode.node_key])
    : null;
  const answerSummary = buildAnswerSummary(preparedSurvey, answers, progress.effectiveCommittedIds);
  const answerReviewItems = buildAnswerReviewItems(preparedSurvey, answers, progress.effectiveCommittedIds);
  const isContinueDisabled = currentNode && currentQuestion
    ? Boolean(validateQuestionAnswer(currentQuestion, answers[currentNode.node_key], currentQuestionState?.required ?? true))
    : false;
  const completionResult: FormFillerResult | null =
    progress.status === "submitted" || progress.status === "discarded"
      ? {
        status: progress.status,
        answers: answerSummary,
        committedQuestionIds: progress.effectiveCommittedIds,
      }
      : null;

  const shouldAutoComplete = completionResult != null
    && !(confirmSubmit && completionResult.status === 'submitted');

  useEffect(() => {
    if (!shouldAutoComplete || !completionResult) {
      lastReportedCompletionKey.current = null;
      return;
    }

    const completionKey = `${completionResult.status}:${completionResult.committedQuestionIds.join("|")}`;
    if (lastReportedCompletionKey.current === completionKey) return;

    lastReportedCompletionKey.current = completionKey;
    onComplete?.(completionResult);
  }, [shouldAutoComplete, completionResult, onComplete]);

  useEffect(() => {
    if (!userConfirmedSubmit || !completionResult) return;
    onComplete?.(completionResult);
  }, [userConfirmedSubmit, completionResult, onComplete]);

  function handleAnswerChange(questionId: string, nextValue: QuestionAnswer) {
    setAnswers((current) => ({
      ...current,
      [questionId]: nextValue,
    }));
    setValidationMessage(null);
  }

  function handleContinue() {
    if (!currentNode || !currentQuestion) return;

    const error = validateQuestionAnswer(
      currentQuestion,
      answers[currentNode.node_key],
      currentQuestionState?.required ?? true,
    );

    if (error) {
      setValidationMessage(error);
      return;
    }

    setValidationMessage(null);
    const committedAnswer = answers[currentNode.node_key];
    if (committedAnswer !== undefined) {
      onAnswerCommit?.(currentNode.node_key, committedAnswer);
    }
    setCommittedQuestionIds([...progress.effectiveCommittedIds, currentNode.node_key]);
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
      <section className="box-border grid min-h-screen place-items-center px-8 py-9 max-sm:px-4.5 max-sm:py-6">
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
    <section className="box-border grid min-h-screen place-items-center px-8 py-9 max-sm:px-4.5 max-sm:py-6">
      <div
        className={[
          "mx-auto w-full",
          isSingleColumn
            ? "flex max-w-[1120px] justify-center"
            : "grid max-w-[1360px] grid-cols-[minmax(0,1fr)_320px] items-start gap-6 max-[920px]:grid-cols-1",
        ].join(" ")}
      >
        <div className={panelClass}>
          {progress.status === "active" && currentNode && currentQuestion ? (
            <>
              <header className="flex items-start justify-between max-sm:flex-col">
                <div>
                  {currentQuestion.title?.trim() && (
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

              {renderQuestionInput(currentNode, answers[currentNode.node_key], handleAnswerChange)}

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
          ) : progress.status === "invalid" ? (
            <div className="flex flex-col gap-4.5">
              <Badge variant="warning" size="sm">Survey error</Badge>
              <h1 className="m-0 text-[clamp(1.7rem,4vw,2.4rem)] text-foreground">
                This survey can&apos;t be completed
              </h1>
              <p className="m-0 leading-relaxed text-muted-foreground">
                {progress.error ?? "The survey rules are misconfigured."}
              </p>
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
          ) : confirmSubmit && completionResult?.status === "submitted" && !userConfirmedSubmit ? (
            <div className="flex flex-col gap-4.5">
              <Badge variant="accent" size="sm">Ready to submit</Badge>
              <h1 className="m-0 text-[clamp(1.7rem,4vw,2.4rem)] text-foreground">
                Review your answers
              </h1>
              <p className="m-0 leading-relaxed text-muted-foreground">
                You&apos;ve answered all the questions. When you&apos;re ready, click submit to send your response.
              </p>
              {showAnswerSummary && renderAnswerReview(answerReviewItems)}
              <div className="flex flex-wrap gap-3">
                <Button type="button" variant="primary" onClick={() => setUserConfirmedSubmit(true)}>
                  {submitLabel}
                </Button>
                <Button type="button" variant="secondary" onClick={handleBack}>
                  Back
                </Button>
                {onExit && (
                  <Button type="button" variant="secondary" onClick={onExit}>
                    {exitLabel}
                  </Button>
                )}
              </div>
            </div>
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
              {showAnswerSummary && renderAnswerReview(answerReviewItems)}
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

// Submission entries carry the readable node_key snapshot alongside the answer.
// node_key also identifies the answer internally, so no extra id is needed.
function buildAnswerSummary(
  preparedSurvey: PreparedSurvey,
  answers: AnswerMap,
  committedQuestionIds: string[],
): SubmissionAnswer[] {
  return committedQuestionIds.flatMap((questionId) => {
    const node = preparedSurvey.questionById.get(questionId);
    if (!node) return [];
    return [{ question_key: node.node_key, answer: answers[questionId] ?? null }];
  });
}

function buildAnswerReviewItems(
  preparedSurvey: PreparedSurvey,
  answers: AnswerMap,
  committedQuestionIds: string[],
): AnswerReviewItem[] {
  return committedQuestionIds.flatMap((questionId, index) => {
    const node = preparedSurvey.questionById.get(questionId);
    if (!node) return [];

    return [{
      questionKey: node.node_key,
      title: node.content.title?.trim() || `Question ${index + 1}`,
      prompt: node.content.label || "Untitled question",
      answer: formatReviewAnswer(node, answers[questionId]),
    }];
  });
}

function renderAnswerReview(items: AnswerReviewItem[]) {
  if (items.length === 0) {
    return (
      <div className="rounded-2xl border border-border bg-muted/20 px-4 py-3 text-sm text-muted-foreground">
        No answers recorded.
      </div>
    );
  }

  return (
    <section className="flex flex-col gap-3.5" aria-label="Answer summary">
      <div className="flex items-center justify-between gap-3">
        <h2 className="m-0 text-[0.92rem] font-semibold uppercase tracking-[0.04em] text-muted-foreground">
          Your answers
        </h2>
        <span className="text-sm text-muted-foreground">
          {items.length} {items.length === 1 ? "answer" : "answers"}
        </span>
      </div>
      <ol className="m-0 flex list-none flex-col gap-3 p-0">
        {items.map((item, index) => (
          <li
            key={item.questionKey}
            className="rounded-2xl border border-border bg-muted/20 p-4"
          >
            <div className="flex gap-3.5">
              <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-accent/15 text-sm font-semibold text-accent">
                {index + 1}
              </span>
              <div className="flex min-w-0 flex-1 flex-col gap-3">
                <div className="flex flex-col gap-1.5">
                  <h3 className="m-0 break-words text-base font-semibold leading-tight text-foreground">
                    {item.title}
                  </h3>
                  <p className="m-0 whitespace-pre-wrap break-words text-sm leading-relaxed text-muted-foreground">
                    {item.prompt}
                  </p>
                </div>
                {Array.isArray(item.answer) ? (
                  <ul className="m-0 flex list-none flex-col gap-2 p-0">
                    {item.answer.map((line, lineIndex) => (
                      <li
                        key={`${item.questionKey}-${lineIndex}`}
                        className="rounded-xl bg-card px-3.5 py-2.5 text-sm font-medium leading-relaxed text-foreground"
                      >
                        {line}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="m-0 rounded-xl bg-card px-3.5 py-2.5 text-sm font-medium leading-relaxed text-foreground">
                    {item.answer}
                  </p>
                )}
              </div>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

function formatReviewAnswer(node: QuestionNode, answer: QuestionAnswer | undefined): string | string[] {
  const emptyAnswerText = "No answer provided";
  const question = node.content;

  switch (question.family) {
    case "choice": {
      if (!Array.isArray(answer) || answer.length === 0) return emptyAnswerText;

      const labelById = new Map(question.definition.options.map((option) => [option.id, option.label || option.id]));
      return answer.map((optionId) => labelById.get(optionId) ?? optionId);
    }

    case "matching": {
      const selectedPairs = toRecord(answer);
      const matchLabelById = new Map(question.definition.matches.map((match) => [match.id, match.label || match.id]));
      const formattedPairs = question.definition.prompts.flatMap((prompt) => {
        const matchId = selectedPairs[prompt.id];
        if (!matchId) return [];

        return [`${prompt.label || prompt.id} -> ${matchLabelById.get(matchId) ?? matchId}`];
      });

      return formattedPairs.length > 0 ? formattedPairs : emptyAnswerText;
    }

    case "rating": {
      if (typeof answer !== "number") return emptyAnswerText;

      const definition = question.definition;
      if (definition.variant === "stars") {
        return `${answer} of ${definition.stars} stars`;
      }

      if (definition.variant === "emoji") {
        const label = getEmojiRatingLabel(definition.emoji_list, answer);
        return label ? `${label} (${answer} of 5)` : `${answer} of 5`;
      }

      const leftLabel = definition.ui.left_label || "Low";
      const rightLabel = definition.ui.right_label || "High";
      return `${answer} (${leftLabel} to ${rightLabel})`;
    }

    case "field":
      return typeof answer === "string" && answer.trim() ? answer : emptyAnswerText;
    default:
      return emptyAnswerText;
  }
}

function getEmojiRatingLabel(emojiList: "sad_to_happy" | "angry_to_happy" | "disgust_to_happy", value: number) {
  const labelsByList: Record<typeof emojiList, string[]> = {
    sad_to_happy: ["Sad", "Low", "Neutral", "Good", "Happy"],
    angry_to_happy: ["Angry", "Tense", "Neutral", "Calm", "Happy"],
    disgust_to_happy: ["Disgusted", "Uneasy", "Neutral", "Pleased", "Happy"],
  };

  return labelsByList[emojiList][value - 1] ?? null;
}

function renderQuestionInput(
  node: QuestionNode,
  answer: QuestionAnswer | undefined,
  onChange: (questionId: string, nextValue: QuestionAnswer) => void,
) {
  const question = node.content;
  switch (question.family) {
    case "choice":
      return (
        <MultiChoiceFormFiller
          question={question}
          value={Array.isArray(answer) ? answer.filter((value): value is string => typeof value === "string") : []}
          onChange={(nextValue) => onChange(node.node_key, nextValue)}
        />
      );
    case "matching":
      return (
        <MatchingFormFiller
          question={question}
          value={toRecord(answer)}
          onChange={(nextValue) => onChange(node.node_key, nextValue)}
        />
      );
    case "rating":
      return (
        <RatingFormFiller
          question={question}
          value={typeof answer === "number" ? answer : null}
          onChange={(nextValue) => onChange(node.node_key, nextValue)}
        />
      );
    case "field":
      return (
        <FieldFormFiller
          question={question}
          value={typeof answer === "string" ? answer : ""}
          onChange={(nextValue) => onChange(node.node_key, nextValue)}
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
