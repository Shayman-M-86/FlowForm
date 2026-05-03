import { Fragment, type ReactNode, useEffect, useLayoutEffect, useRef, useState, } from "react";
import { useNavigate } from "react-router-dom";
import type { FieldQuestionHandle } from "../components/node/FieldQuestion";
import type { MatchingQuestionHandle } from "../components/node/MatchingQuestion";
import type { MultiChoiceQuestionHandle } from "../components/node/MultiChoiceQuestion";
import type { RatingQuestionHandle } from "../components/node/RatingQuestion";
import type { RulesQuestionHandle } from "../components/node/RulesQuestion";
import { Badge, Button, Input, Select, ThemeToggle } from "@flowform/ui";
import { FieldQuestion } from "../components/node/FieldQuestion";
import { MatchingQuestion } from "../components/node/MatchingQuestion";
import { MultiChoiceQuestion } from "../components/node/MultiChoiceQuestion";
import { RatingQuestion } from "../components/node/RatingQuestion";
import { RulesQuestion } from "../components/node/RulesQuestion";
import { savePreviewSurvey } from "../components/form_filler/previewStorage";
import type { QuestionContent, RuleContent, SurveyNode } from "../components/node/questionTypes";
import { serializeSurveyEntries, type SurveyEntry } from "../components/node/surveySerialize";
import { incrementQuestionId } from "../components/node/NodePillUtils";
import { NodePillMobileControlsProvider } from "../components/node/NodePillShell";

const DEBUG_SHOW_JSON = false;
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

  .node-page__toolbar-search-input.input-field,
  .node-page__toolbar-filter.select-field {
    gap: 0;
  }

  .node-page__toolbar-search-input .input-control,
  .node-page__toolbar-filter .select-control {
    height: 100%;
    border: none;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
  }

  .node-page__toolbar-search-input .input-control {
    border-right: 1px solid var(--border);
  }

  .node-page__toolbar-search-input .input-control:focus,
  .node-page__toolbar-filter .select-control:focus {
    box-shadow: inset 0 0 0 1px var(--accent-border), var(--focus-ring);
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
  searchQuery: string;
  filterType: "all" | QuestionType;
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
      searchQuery: typeof parsed.searchQuery === "string" ? parsed.searchQuery : "",
      filterType:
        parsed.filterType === "all" ||
        parsed.filterType === "multi-choice" ||
        parsed.filterType === "matching" ||
        parsed.filterType === "rating" ||
        parsed.filterType === "field" ||
        parsed.filterType === "rules"
          ? parsed.filterType
          : "all",
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

export function NodePage() {
  const navigate = useNavigate();
  const persistedState = useRef<PersistedNodePageState | null>(loadPersistedNodePageState());
  const persistedUiState = useRef<PersistedNodePageUiState | null>(loadPersistedNodePageUiState());
  const [questions, setQuestions] = useState<Question[]>(() => persistedState.current?.questions ?? []);
  const [nextId, setNextId] = useState(() => persistedState.current?.nextId ?? 1);
  const [editingQuestionIds, setEditingQuestionIds] = useState<string[]>([]);
  const [questionContents, setQuestionContents] = useState<Record<string, QuestionContent>>(
    () => persistedState.current?.questionContents ?? {},
  );
  const [ruleContents, setRuleContents] = useState<Record<string, RuleContent>>(
    () => persistedState.current?.ruleContents ?? {},
  );
  const [searchQuery, setSearchQuery] = useState(() => persistedUiState.current?.searchQuery ?? "");
  const [filterType, setFilterType] = useState<"all" | QuestionType>(() => persistedUiState.current?.filterType ?? "all");
  const [collapsedIds, setCollapsedIds] = useState<Set<string>>(() => new Set(persistedUiState.current?.collapsedIds ?? []));
  const questionRefsMap = useRef<Map<string, FieldQuestionHandle | MatchingQuestionHandle | MultiChoiceQuestionHandle | RatingQuestionHandle | RulesQuestionHandle>>(new Map());
  const questionWrapperNodeMap = useRef<Map<string, HTMLDivElement>>(new Map());
  const pendingMoveAnimation = useRef<{
    positions: Map<string, number>;
    movedId: string;
  } | null>(null);
  const newlyAddedQuestionId = useRef<string | null>(null);
  const duplicateQuestionIds = new Set(
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
  );
  const hasDuplicateIds = duplicateQuestionIds.size > 0;

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

  function addQuestion(type: QuestionType) {
    const newId = `q${nextId}`;
    newlyAddedQuestionId.current = newId;
    setQuestions((current) => {
      const initialTag = computeNextTag(current, type);
      return [...current, { id: newId, type, initialTag }];
    });
    setNextId((current) => current + 1);
    setEditingQuestionIds((current) =>
      current.includes(newId) ? current : [...current, newId],
    );
  }

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
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(NODE_PAGE_STORAGE_KEY);
      window.localStorage.removeItem(NODE_PAGE_UI_STORAGE_KEY);
    }

    setQuestions([]);
    setNextId(1);
    setEditingQuestionIds([]);
    setQuestionContents({});
    setRuleContents({});
    setSearchQuery("");
    setFilterType("all");
    setCollapsedIds(new Set());
    questionRefsMap.current.clear();
    questionWrapperNodeMap.current.clear();
    pendingMoveAnimation.current = null;
    newlyAddedQuestionId.current = null;
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
    const handleContentChange = (content: QuestionContent) => {
      setQuestionContents((current) => (
        areContentsEqual(current[question.id], content)
          ? current
          : {
            ...current,
            [question.id]: content,
          }
      ));
    };
    const handleRuleContentChange = (content: RuleContent) => {
      setRuleContents((current) => (
        areContentsEqual(current[question.id], content)
          ? current
          : {
            ...current,
            [question.id]: content,
          }
      ));
    };
    const currentQuestionContent = questionContents[question.id];
    const currentRuleContent = ruleContents[question.id];
    const ruleIndex = questions.findIndex((q) => q.id === question.id);
    const collectContents = (slice: typeof questions) =>
      slice
        .filter((q) => q.type !== "rules")
        .map((q) => questionContents[q.id])
        .filter((content): content is QuestionContent => Boolean(content));
    const previousSiblings = collectContents(questions.slice(0, ruleIndex));
    const followingSiblings = collectContents(questions.slice(ruleIndex + 1));

    const isCollapsed = collapsedIds.has(question.id);
    const idError = duplicateQuestionIds.has(question.id) ? "ID must be unique." : undefined;
    const onExpand = () => {
      setCollapsedIds((current) => {
        const next = new Set(current);
        next.delete(question.id);
        return next;
      });
      setEditingQuestionIds((current) => current.includes(question.id) ? current : [...current, question.id]);
    };

    switch (question.type) {
      case "multi-choice":
        return <MultiChoiceQuestion key={key} ref={handleRef} initialTag={question.initialTag} initialContent={currentQuestionContent?.family === "choice" ? currentQuestionContent : undefined} idError={idError} isCollapsed={isCollapsed} onExpand={onExpand} onDelete={() => removeQuestion(question.id)} onEditModeChange={handleEditModeChange} onDataChange={handleContentChange} />;
      case "matching":
        return <MatchingQuestion key={key} ref={handleRef} initialTag={question.initialTag} initialContent={currentQuestionContent?.family === "matching" ? currentQuestionContent : undefined} idError={idError} isCollapsed={isCollapsed} onExpand={onExpand} onDelete={() => removeQuestion(question.id)} onEditModeChange={handleEditModeChange} onDataChange={handleContentChange} />;
      case "rating":
        return <RatingQuestion key={key} ref={handleRef} initialTag={question.initialTag} initialContent={currentQuestionContent?.family === "rating" ? currentQuestionContent : undefined} idError={idError} isCollapsed={isCollapsed} onExpand={onExpand} onDelete={() => removeQuestion(question.id)} onEditModeChange={handleEditModeChange} onDataChange={handleContentChange} />;
      case "field":
        return <FieldQuestion key={key} ref={handleRef} initialTag={question.initialTag} initialContent={currentQuestionContent?.family === "field" ? currentQuestionContent : undefined} idError={idError} isCollapsed={isCollapsed} onExpand={onExpand} onDelete={() => removeQuestion(question.id)} onEditModeChange={handleEditModeChange} onDataChange={handleContentChange} />;
      case "rules":
        return <RulesQuestion key={key} ref={handleRef} initialTag={question.initialTag} initialContent={currentRuleContent} idError={idError} isCollapsed={isCollapsed} onExpand={onExpand} onDelete={() => removeQuestion(question.id)} onEditModeChange={handleEditModeChange} onDataChange={handleRuleContentChange} previousSiblings={previousSiblings} followingSiblings={followingSiblings} />;
    }
  }

  const addQuestionCard = (
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
  );

  const getQuestionSearchTokens = (question: Question) => {
    if (question.type === "rules") {
      const rule = ruleContents[question.id];
      return { title: "Rule", id: rule?.id ?? question.initialTag };
    }
    const content = questionContents[question.id];
    return { title: content?.title ?? "", id: content?.id ?? question.initialTag };
  };

  const isQuestionExpanded = (question: Question) => {
    if (collapsedIds.has(question.id)) return false;
    const { title, id } = getQuestionSearchTokens(question);
    const normalizedSearch = searchQuery.trim().toLowerCase();
    const matchesFilter = filterType === "all" || question.type === filterType;
    const matchesSearch =
      normalizedSearch === "" ||
      `${title || "Untitled question"} ${id}`.toLowerCase().includes(normalizedSearch);
    return matchesFilter && matchesSearch;
  };

  function toggleCollapsed(id: string) {
    setCollapsedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const serializeSurvey = () => {
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
  };

  const serializedSurvey = serializeSurvey();

  useEffect(() => {
    if (typeof window === "undefined") return;

    try {
      window.localStorage.setItem(NODE_PAGE_STORAGE_KEY, JSON.stringify(serializedSurvey));
    } catch {
      // Ignore persistence failures.
    }
  }, [serializedSurvey]);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const questionIds = new Set(questions.map((question) => question.id));
    const uiState: PersistedNodePageUiState = {
      collapsedIds: Array.from(collapsedIds).filter((id) => questionIds.has(id)),
      searchQuery,
      filterType,
    };

    try {
      window.localStorage.setItem(NODE_PAGE_UI_STORAGE_KEY, JSON.stringify(uiState));
    } catch {
      // Ignore persistence failures.
    }
  }, [collapsedIds, filterType, questions, searchQuery]);

  function handlePreview() {
    if (serializedSurvey.length === 0) return;
    savePreviewSurvey(serializedSurvey);
    navigate("/node/preview", { state: { survey: serializedSurvey } });
  }

  return (
    <section className="node-page flex min-h-full flex-col">
      <style dangerouslySetInnerHTML={{ __html: NODE_PAGE_STYLES }} />
      <div className="node-page__toolbar fixed left-[var(--sidebar-w)] right-0 top-0 z-20 box-border flex h-[var(--node-page-toolbar-height)] items-center justify-center border-b border-border bg-[var(--toolbar-bg)] px-6 py-[14px] backdrop-blur-[14px] max-[640px]:left-0 max-[640px]:px-4">
        <div className="node-page__toolbar-shell flex w-full max-w-[980px] items-center gap-3 max-[640px]:flex-col max-[640px]:items-stretch">
          <div className="node-page__toolbar-header flex min-w-0 flex-1 items-stretch overflow-hidden rounded-[999px] border border-border bg-[var(--bg-subtle)] shadow-sm max-[640px]:w-full">
            <h4 className="m-0 flex items-center border-r border-border px-[18px] text-[0.82rem] font-semibold uppercase tracking-[0.08em] text-[var(--text-soft)] max-[640px]:px-[14px]">
              Search
            </h4>
            <Input
              className="node-page__toolbar-search-input min-w-0 flex-1"
              placeholder="Search by title or ID"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
            />
            <Select
              className="node-page__toolbar-filter min-w-0 basis-[240px] max-[640px]:basis-[200px]"
              value={filterType}
              options={[
                { value: "all", label: "All question types" },
                ...QUESTION_TYPE_OPTIONS,
              ]}
              onChange={(event) => setFilterType(event.target.value as "all" | QuestionType)}
            />
          </div>
          <div className="node-page__toolbar-actions flex shrink-0 items-center gap-2.5 max-[640px]:w-full">
            <ThemeToggle />
            <Button
              className="max-[640px]:flex-1"
              type="button"
              variant="ghost"
              size="sm"
              onClick={clearSchema}
              disabled={questions.length === 0}
            >
              Clear
            </Button>
            <Button
              className="max-[640px]:flex-1"
              type="button"
              variant="secondary"
              size="sm"
              onClick={handlePreview}
              disabled={serializedSurvey.length === 0 || hasDuplicateIds}
            >
              Preview form
            </Button>
          </div>
        </div>
      </div>
      <div className="node-page__content box-border flex w-full max-w-[calc(980px+(var(--node-page-controls-gutter)*2))] shrink-0 flex-col items-center self-center px-[var(--node-page-controls-gutter)] pb-10 pt-[calc(var(--node-page-toolbar-height)+var(--node-page-toolbar-gap))] max-[640px]:gap-[14px] max-[640px]:px-5 max-[640px]:pt-[calc(var(--node-page-toolbar-height)+var(--node-page-toolbar-gap)+10px)]">
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
      {DEBUG_SHOW_JSON && (
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
          variant="ghost"
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
              <Button
                className="min-h-7 min-w-7 p-0 text-[0.8rem] text-(--text-soft)"
                type="button"
                variant="ghost"
                size="xs"
                aria-label={isExpanded ? "Collapse question" : "Expand question"}
                aria-expanded={isExpanded}
                onClick={onToggleCollapse}
              >
                {isExpanded ? "▾" : "▸"}
              </Button>
            ),
            trailing: isEditing ? (
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
            ) : undefined,
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
