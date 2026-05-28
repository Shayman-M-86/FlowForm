import { Fragment, type ReactNode, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, } from "react";
import { useNavigate } from "react-router-dom";
import { Play, Sparkles, Trash2 } from "lucide-react";
import type { FieldQuestionHandle } from "../components/node/FieldQuestion";
import type { MatchingQuestionHandle } from "../components/node/MatchingQuestion";
import type { MultiChoiceQuestionHandle } from "../components/node/MultiChoiceQuestion";
import type { RatingQuestionHandle } from "../components/node/RatingQuestion";
import type { RulesQuestionHandle } from "../components/node/RulesQuestion";
import { Badge, Button } from "@flowform/ui";
import { FieldQuestion } from "../components/node/FieldQuestion";
import { MatchingQuestion } from "../components/node/MatchingQuestion";
import { MultiChoiceQuestion } from "../components/node/MultiChoiceQuestion";
import { RatingQuestion } from "../components/node/RatingQuestion";
import { RulesQuestion } from "../components/node/RulesQuestion";
import { savePreviewSurvey } from "../components/form_filler/previewStorage";
import type { QuestionContent, RuleContent, SurveyNode } from "../components/node/questionTypes";
import { serializeSurveyEntries, type SurveyEntry } from "../components/node/surveySerialize";
import { AiImportModal } from "../components/node/AiImportModal";
import { incrementQuestionId } from "../components/node/NodePillUtils";
import { NodePillMobileControlsProvider } from "../components/node/NodePillShell";
import { PlusGridAnimation } from "../components/node/PlusGridAnimation";

const NODE_PAGE_STORAGE_KEY = "flowform.node-page.schema";
const NODE_PAGE_UI_STORAGE_KEY = "flowform.node-page.ui";
const NODE_PAGE_STYLES = `
  .node-page {
    --node-page-controls-gutter: 52px;
    --node-page-toolbar-height: 86.5px;
    --node-page-toolbar-gap: 20px;
    --sab: env(safe-area-inset-bottom, 0px);
  }

  .node-page__content {
    padding-bottom: var(--sab);
  }

  .node-page__question-wrapper--collapsed + .node-page__question-wrapper--collapsed {
    margin-top: -10px;
  }

  .node-page__question-content--hidden {
    display: none;
  }

  .node-page__question-summary-id {
    color: var(--text-soft);
    font-size: 0.78rem;
  }

  @media (max-width: 640px) {
    .node-page {
      --node-page-controls-gutter: 0px;
      --node-page-toolbar-gap: 14px;
    }
  }
`;

type QuestionType = "multi-choice" | "matching" | "rating" | "field" | "rules";

interface Question {
  id: string;
  type: QuestionType;
  initialTag: string;
}

interface PersistedNodePageState {
  questions: Question[];
  nextId: number;
  questionContents: Record<string, QuestionContent>;
  ruleContents: Record<string, RuleContent>;
}

interface PersistedNodePageUiState {
  collapsedIds: string[];
}

function loadPersistedNodePageState(): PersistedNodePageState | null {
  if (typeof window === "undefined") return null;

  try {
    const stored = window.localStorage.getItem(NODE_PAGE_STORAGE_KEY);
    if (!stored) return null;

    const parsed: unknown = JSON.parse(stored);

    if (Array.isArray(parsed)) {
      return deserializeSurveyNodes(parsed);
    }

    if (parsed && typeof parsed === "object") {
      const legacy = parsed as Partial<PersistedNodePageState>;
      if (Array.isArray(legacy.questions)) {
        return {
          questions: legacy.questions,
          nextId: typeof legacy.nextId === "number" && Number.isFinite(legacy.nextId) ? legacy.nextId : 1,
          questionContents: legacy.questionContents && typeof legacy.questionContents === "object"
            ? legacy.questionContents as Record<string, QuestionContent>
            : {},
          ruleContents: legacy.ruleContents && typeof legacy.ruleContents === "object"
            ? legacy.ruleContents as Record<string, RuleContent>
            : {},
        };
      }
    }

    return null;
  } catch {
    return null;
  }
}

function deserializeSurveyNodes(nodes: SurveyNode[]): PersistedNodePageState {
  const orderedNodes = [...nodes].sort((left, right) => left.sort_key - right.sort_key);
  const questions: Question[] = [];
  const questionContents: Record<string, QuestionContent> = {};
  const ruleContents: Record<string, RuleContent> = {};

  orderedNodes.forEach((node, index) => {
    const internalId = `q${index + 1}`;

    if (node.type === "rule") {
      questions.push({
        id: internalId,
        type: "rules",
        initialTag: node.content.id,
      });
      ruleContents[internalId] = node.content;
      return;
    }

    questions.push({
      id: internalId,
      type: questionTypeFromContent(node.content),
      initialTag: node.content.id,
    });
    questionContents[internalId] = node.content;
  });

  return {
    questions,
    nextId: questions.length + 1,
    questionContents,
    ruleContents,
  };
}

function questionTypeFromContent(content: QuestionContent): Exclude<QuestionType, "rules"> {
  switch (content.family) {
    case "choice":
      return "multi-choice";
    case "matching":
      return "matching";
    case "rating":
      return "rating";
    case "field":
      return "field";
  }
}

function loadPersistedNodePageUiState(): PersistedNodePageUiState | null {
  if (typeof window === "undefined") return null;

  try {
    const stored = window.localStorage.getItem(NODE_PAGE_UI_STORAGE_KEY);
    if (!stored) return null;

    const parsed = JSON.parse(stored) as Partial<PersistedNodePageUiState>;
    return {
      collapsedIds: Array.isArray(parsed.collapsedIds) ? parsed.collapsedIds.filter((id): id is string => typeof id === "string") : [],
    };
  } catch {
    return null;
  }
}

function areContentsEqual<T>(left: T | undefined, right: T): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}

function getNodeSchemaId(
  question: Question,
  questionContents: Record<string, QuestionContent>,
  ruleContents: Record<string, RuleContent>,
): string {
  if (question.type === "rules") {
    return ruleContents[question.id]?.id ?? question.initialTag;
  }

  return questionContents[question.id]?.id ?? question.initialTag;
}

const QUESTION_TYPE_OPTIONS: Array<{ value: QuestionType; label: string }> = [
  { value: "multi-choice", label: "Multiple choice" },
  { value: "matching", label: "Matching" },
  { value: "rating", label: "Rating" },
  { value: "field", label: "Field" },
  { value: "rules", label: "Rules" },
];

const SWAP_ANIMATION_MS = 280;

interface NodePageProps {
  initialNodes?: SurveyNode[];
  onNodesChange?: (nodes: SurveyNode[]) => void;
  showDebug?: boolean;
}

export function NodePage({ initialNodes, onNodesChange, showDebug }: NodePageProps = {}) {
  const navigate = useNavigate();
  const controlled = initialNodes !== undefined;

  const persistedState = useRef<PersistedNodePageState | null>(
    controlled ? null : loadPersistedNodePageState(),
  );
  const persistedUiState = useRef<PersistedNodePageUiState | null>(
    controlled ? null : loadPersistedNodePageUiState(),
  );

  const initialState = useRef<PersistedNodePageState | null>(
    controlled ? deserializeSurveyNodes(initialNodes) : persistedState.current,
  );

  const [questions, setQuestions] = useState<Question[]>(() => initialState.current?.questions ?? []);
  const [nextId, setNextId] = useState(() => initialState.current?.nextId ?? 1);
  const [editingQuestionIds, setEditingQuestionIds] = useState<string[]>([]);
  const [questionContents, setQuestionContents] = useState<Record<string, QuestionContent>>(
    () => initialState.current?.questionContents ?? {},
  );
  const [ruleContents, setRuleContents] = useState<Record<string, RuleContent>>(
    () => initialState.current?.ruleContents ?? {},
  );
  const [collapsedIds, setCollapsedIds] = useState<Set<string>>(() => new Set(persistedUiState.current?.collapsedIds ?? []));
  const questionRefsMap = useRef<Map<string, FieldQuestionHandle | MatchingQuestionHandle | MultiChoiceQuestionHandle | RatingQuestionHandle | RulesQuestionHandle>>(new Map());
  const questionWrapperNodeMap = useRef<Map<string, HTMLDivElement>>(new Map());
  const pendingMoveAnimation = useRef<{
    positions: Map<string, number>;
    movedId: string;
  } | null>(null);
  const newlyAddedQuestionId = useRef<string | null>(null);
  const duplicateQuestionIds = useMemo(() => new Set(
    Object.entries(
      questions.reduce<Record<string, string[]>>((acc, question) => {
        const schemaId = getNodeSchemaId(question, questionContents, ruleContents).trim();
        if (schemaId === "") return acc;
        acc[schemaId] = [...(acc[schemaId] ?? []), question.id];
        return acc;
      }, {}),
    )
      .filter(([, nodeIds]) => nodeIds.length > 1)
      .flatMap(([, nodeIds]) => nodeIds),
  ), [questions, questionContents, ruleContents]);
  const hasDuplicateIds = duplicateQuestionIds.size > 0;

  const [aiImportOpen, setAiImportOpen] = useState(false);

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

      const questionContainer = questionNode.querySelector<HTMLDivElement>(".node-page__question-container");
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
        const questionContainer = questionNode.querySelector<HTMLDivElement>(".node-page__question-container");
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

  const nextIdRef = useRef(nextId);
  nextIdRef.current = nextId;

  const addQuestion = useCallback((type: QuestionType) => {
    const newId = `q${nextIdRef.current}`;
    newlyAddedQuestionId.current = newId;
    setQuestions((current) => {
      const initialTag = computeNextTag(current, type);
      return [...current, { id: newId, type, initialTag }];
    });
    setNextId((n) => n + 1);
    setEditingQuestionIds((current) =>
      current.includes(newId) ? current : [...current, newId],
    );
  // computeNextTag is a pure function defined in this module scope — no closure deps
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function computeNextTag(currentQuestions: Question[], type: QuestionType): string {
    const isRule = type === "rules";
    const relevant = currentQuestions.filter((q) => (q.type === "rules") === isRule);
    if (relevant.length === 0) return isRule ? "r1" : "question_id_1";
    const lastTag = relevant[relevant.length - 1].initialTag;
    return incrementQuestionId(lastTag);
  }

  function removeQuestion(id: string) {
    setQuestions((current) => current.filter((q) => q.id !== id));
    setEditingQuestionIds((current) => current.filter((questionId) => questionId !== id));
    setQuestionContents((current) => {
      const next = { ...current };
      delete next[id];
      return next;
    });
    setRuleContents((current) => {
      const next = { ...current };
      delete next[id];
      return next;
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

  function clearSchema() {
    if (!controlled && typeof window !== "undefined") {
      window.localStorage.removeItem(NODE_PAGE_STORAGE_KEY);
      window.localStorage.removeItem(NODE_PAGE_UI_STORAGE_KEY);
    }

    setQuestions([]);
    setNextId(1);
    setEditingQuestionIds([]);
    setQuestionContents({});
    setRuleContents({});
    setCollapsedIds(new Set());
    questionRefsMap.current.clear();
    questionWrapperNodeMap.current.clear();
    pendingMoveAnimation.current = null;
    newlyAddedQuestionId.current = null;
  }

  // Precompute sibling content lists once per questions/questionContents change.
  // RulesQuestion uses these to show branching targets — recomputing per-render is O(n²).
  const siblingsMap = useMemo(() => {
    const nonRuleContents = (slice: Question[]) =>
      slice
        .filter((q) => q.type !== "rules")
        .map((q) => questionContents[q.id])
        .filter((c): c is QuestionContent => Boolean(c));

    return new Map(
      questions.map((question, index) => [
        question.id,
        {
          previous: nonRuleContents(questions.slice(0, index)),
          following: nonRuleContents(questions.slice(index + 1)),
        },
      ]),
    );
  }, [questions, questionContents]);

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
    const handleContentChange = (content: QuestionContent) => {
      setQuestionContents((current) => (
        areContentsEqual(current[question.id], content)
          ? current
          : { ...current, [question.id]: content }
      ));
    };
    const handleRuleContentChange = (content: RuleContent) => {
      setRuleContents((current) => (
        areContentsEqual(current[question.id], content)
          ? current
          : { ...current, [question.id]: content }
      ));
    };
    const currentQuestionContent = questionContents[question.id];
    const currentRuleContent = ruleContents[question.id];
    const siblings = siblingsMap.get(question.id);

    const isCollapsed = collapsedIds.has(question.id);
    const isEditMode = editingQuestionIds.includes(question.id);
    const idError = duplicateQuestionIds.has(question.id) ? "ID must be unique." : undefined;
    const onExpand = () => {
      setCollapsedIds((current) => {
        const next = new Set(current);
        next.delete(question.id);
        return next;
      });
    };
    const onExpandInEditMode = () => {
      setCollapsedIds((current) => {
        const next = new Set(current);
        next.delete(question.id);
        return next;
      });
      setEditingQuestionIds((current) =>
        current.includes(question.id) ? current : [...current, question.id],
      );
    };

    const sharedProps = { isCollapsed, isEditMode, idError, onExpand, onExpandInEditMode, onEditModeChange: handleEditModeChange };

    switch (question.type) {
      case "multi-choice":
        return <MultiChoiceQuestion key={key} ref={handleRef} initialTag={question.initialTag} initialContent={currentQuestionContent?.family === "choice" ? currentQuestionContent : undefined} {...sharedProps} onDelete={() => removeQuestion(question.id)} onDataChange={handleContentChange} />;
      case "matching":
        return <MatchingQuestion key={key} ref={handleRef} initialTag={question.initialTag} initialContent={currentQuestionContent?.family === "matching" ? currentQuestionContent : undefined} {...sharedProps} onDelete={() => removeQuestion(question.id)} onDataChange={handleContentChange} />;
      case "rating":
        return <RatingQuestion key={key} ref={handleRef} initialTag={question.initialTag} initialContent={currentQuestionContent?.family === "rating" ? currentQuestionContent : undefined} {...sharedProps} onDelete={() => removeQuestion(question.id)} onDataChange={handleContentChange} />;
      case "field":
        return <FieldQuestion key={key} ref={handleRef} initialTag={question.initialTag} initialContent={currentQuestionContent?.family === "field" ? currentQuestionContent : undefined} {...sharedProps} onDelete={() => removeQuestion(question.id)} onDataChange={handleContentChange} />;
      case "rules":
        return <RulesQuestion key={key} ref={handleRef} initialTag={question.initialTag} initialContent={currentRuleContent} {...sharedProps} onDelete={() => removeQuestion(question.id)} onDataChange={handleRuleContentChange} previousSiblings={siblings?.previous ?? []} followingSiblings={siblings?.following ?? []} />;
    }
  }

  const addQuestionCard = useMemo(() => (
    <div className="flex flex-col items-stretch gap-[18px] rounded-2xl border border-border bg-[image:var(--surface-lift-gradient-faint),var(--bg-subtle)] px-[26px] py-6 shadow-[inset_0_1px_0_var(--overlay-faint)] my-[10px] mb-[60px]">
      <div className="flex flex-col items-start gap-2">
        <Badge variant="accent" size="sm">Build</Badge>
        <p className="m-0 text-base font-semibold text-[var(--text-h)]">Add another question</p>
        <p className="m-0 text-[0.88rem] text-[var(--text-soft)]">
          Choose the next response format to keep building the flow.
        </p>
      </div>
      <div className="flex flex-wrap justify-start gap-2.5">
        {QUESTION_TYPE_OPTIONS.map((option) => (
          <Button
            key={option.value}
            className="min-w-[150px] justify-start"
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
  ), [addQuestion]);

  const isQuestionExpanded = (question: Question) => {
    return !collapsedIds.has(question.id);
  };

  function toggleCollapsed(id: string) {
    setCollapsedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
        setEditingQuestionIds((editing) => editing.filter((qId) => qId !== id));
      }
      return next;
    });
  }

  const serializedSurvey = useMemo(() => {
    const entries: SurveyEntry[] = [];
    for (const question of questions) {
      if (question.type === "rules") {
        const rule = ruleContents[question.id];
        if (rule) entries.push({ kind: "rule", content: rule });
      } else {
        const content = questionContents[question.id];
        if (content) entries.push({ kind: "question", content });
      }
    }
    return serializeSurveyEntries(entries);
  }, [questions, questionContents, ruleContents]);

  const onNodesChangeRef = useRef(onNodesChange);
  onNodesChangeRef.current = onNodesChange;

  useEffect(() => {
    if (controlled) {
      onNodesChangeRef.current?.(serializedSurvey);
      return;
    }

    if (typeof window === "undefined") return;
    try {
      window.localStorage.setItem(NODE_PAGE_STORAGE_KEY, JSON.stringify(serializedSurvey));
    } catch {
      // Ignore persistence failures.
    }
  }, [serializedSurvey, controlled]);

  useEffect(() => {
    if (controlled) return;
    if (typeof window === "undefined") return;

    const questionIds = new Set(questions.map((question) => question.id));
    const uiState: PersistedNodePageUiState = {
      collapsedIds: Array.from(collapsedIds).filter((id) => questionIds.has(id)),
    };

    try {
      window.localStorage.setItem(NODE_PAGE_UI_STORAGE_KEY, JSON.stringify(uiState));
    } catch {
      // Ignore persistence failures.
    }
  }, [collapsedIds, questions, controlled]);

  function handlePreview() {
    if (serializedSurvey.length === 0) return;
    savePreviewSurvey(serializedSurvey);
    navigate("/node/preview", { state: { survey: serializedSurvey } });
  }

  function handleAiImport(nodes: SurveyNode[]) {
    const deserialized = deserializeSurveyNodes(nodes);
    setQuestions(deserialized.questions);
    setNextId(deserialized.nextId);
    setQuestionContents(deserialized.questionContents);
    setRuleContents(deserialized.ruleContents);
    setEditingQuestionIds([]);
    setCollapsedIds(new Set());
    questionRefsMap.current.clear();
    questionWrapperNodeMap.current.clear();
    setAiImportOpen(false);
  }

  return (
    <section className="node-page relative isolate flex min-h-full flex-col mt-0.5 overflow-x-clip">
      <style dangerouslySetInnerHTML={{ __html: NODE_PAGE_STYLES }} />
      <PlusGridAnimation />
      <div className="node-page__toolbar sticky top-0 z-20 box-border flex h-[var(--node-page-toolbar-height)] w-full items-center justify-center border-b border-border bg-[var(--toolbar-bg)] px-6 py-[14px] backdrop-blur-[14px] max-[640px]:px-4">
        <div className="node-page__toolbar-shell flex w-full max-w-[980px] items-center justify-between gap-3">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setAiImportOpen(true)}
          >
            <Sparkles size={14} aria-hidden="true" />
            AI import
          </Button>
          <div className="node-page__toolbar-actions flex shrink-0 items-center gap-2.5">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={clearSchema}
              disabled={questions.length === 0}
            >
              <Trash2 size={14} aria-hidden="true" />
              Clear
            </Button>
            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={handlePreview}
              disabled={serializedSurvey.length === 0 || hasDuplicateIds}
            >
              <Play size={14} aria-hidden="true" />
              Preview form
            </Button>
          </div>
        </div>
      </div>
      <div className="node-page__content relative z-10 box-border flex w-full max-w-[calc(980px+(var(--node-page-controls-gutter)*2))] shrink-0 flex-col items-center self-center px-[var(--node-page-controls-gutter)] pb-10 pt-(--node-page-toolbar-gap) max-[640px]:gap-[14px] max-[640px]:px-5 max-[640px]:pt-[calc(var(--node-page-toolbar-gap)+10px)]">
        <div className="node-page__questions-stack flex w-full flex-col gap-5">
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
                  isEditing={editingQuestionIds.includes(question.id)}
                  isExpanded={isQuestionExpanded(question)}
                  onToggleCollapse={() => toggleCollapsed(question.id)}
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
                  <div className="my-2 h-px bg-border" />
                )}

                {index === questions.length - 1 && (
                  <>
                    <div className="node-page__section-divider my-2 h-px bg-border" />
                    {addQuestionCard}
                  </>
                )}
              </Fragment>
            );
          })}
          {questions.length === 0 && addQuestionCard}
        </div>
      </div>
      <AiImportModal
        open={aiImportOpen}
        hasExistingQuestions={questions.length > 0}
        onClose={() => setAiImportOpen(false)}
        onImport={handleAiImport}
      />

      {showDebug && (
        <aside className="fixed bottom-4 right-4 z-50 flex max-h-[60vh] w-[min(420px,calc(100vw-32px))] flex-col overflow-hidden rounded-xl border border-border bg-[var(--debug-bg)] font-mono text-[0.78rem] text-[var(--debug-text)] shadow max-[640px]:right-4">
          <header className="flex items-center justify-between border-b border-[var(--debug-border)] px-3 py-2 text-[0.72rem] font-semibold uppercase tracking-[0.04em]">
            <span>Debug · survey JSON</span>
            <span className="font-medium text-[var(--debug-text-dim)]">{questions.length} node{questions.length === 1 ? "" : "s"}</span>
          </header>
          <pre className="m-0 overflow-auto whitespace-pre p-3 leading-[1.45]">{JSON.stringify(serializedSurvey, null, 2)}</pre>
        </aside>
      )}
    </section>
  );
}

function QuestionRow({
  question,
  index,
  isLast,
  isEditing,
  isExpanded,
  onToggleCollapse,
  onMoveQuestion,
  onSetWrapperNode,
  children,
}: {
  question: Question;
  index: number;
  isLast: boolean;
  isEditing: boolean;
  isExpanded: boolean;
  onToggleCollapse: () => void;
  onMoveQuestion: (id: string, direction: "up" | "down") => void;
  onSetWrapperNode: (node: HTMLDivElement | null) => void;
  children: ReactNode;
}) {
  return (
    <div
      ref={onSetWrapperNode}
      className={`node-page__question-wrapper flex flex-col ${isExpanded ? "" : "node-page__question-wrapper--collapsed"}`}
    >
      <div className="node-page__question-row relative flex items-start gap-2 max-[640px]:flex-col">
        <Button
          className="node-page__question-collapse-btn absolute left-[calc(-1*var(--node-page-controls-gutter)+10px)] top-[14px] z-[1] min-h-7 min-w-7 p-0 text-[0.8rem] text-[var(--text-soft)] max-[640px]:hidden"
          type="button"
          variant="secondary"
          size="xs"
          aria-label={isExpanded ? "Collapse question" : "Expand question"}
          aria-expanded={isExpanded}
          onClick={onToggleCollapse}
        >
          {isExpanded ? "▾" : "▸"}
        </Button>

        <div className="node-page__question-container relative flex min-w-0 w-full flex-1 flex-col gap-3">
          <NodePillMobileControlsProvider value={{
            leading: (
              <>
                <Button
                  className="min-h-7 min-w-7 p-0 text-[0.8rem] text-(--text-soft)"
                  type="button"
                  variant="secondary"
                  size="xs"
                  aria-label={isExpanded ? "Collapse question" : "Expand question"}
                  aria-expanded={isExpanded}
                  onClick={onToggleCollapse}
                >
                  {isExpanded ? "▾" : "▸"}
                </Button>
                {isEditing && (
                  <>
                    <Button
                      className="min-h-[30px] min-w-[30px] p-0"
                      type="button"
                      variant="ghost"
                      size="sm"
                      disabled={index === 0}
                      aria-label="Move question up"
                      onClick={() => onMoveQuestion(question.id, "up")}
                    >
                      ↑
                    </Button>
                    <Button
                      className="min-h-[30px] min-w-[30px] p-0"
                      type="button"
                      variant="ghost"
                      size="sm"
                      disabled={isLast}
                      aria-label="Move question down"
                      onClick={() => onMoveQuestion(question.id, "down")}
                    >
                      ↓
                    </Button>
                  </>
                )}
              </>
            ),
          }}>
            {children}
          </NodePillMobileControlsProvider>
        </div>

        {isExpanded && isEditing && (
          <div className="node-page__question-move-controls absolute right-[-52px] top-3 inline-flex flex-col gap-2 max-[640px]:hidden" aria-label="Move question">
            <Button
              className="min-w-[34px] p-0"
              type="button"
              variant="ghost"
              size="xs"
              disabled={index === 0}
              aria-label="Move question up"
              onClick={() => onMoveQuestion(question.id, "up")}
            >
              ↑
            </Button>
            <Button
              className="min-w-[34px] p-0"
              type="button"
              variant="ghost"
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
