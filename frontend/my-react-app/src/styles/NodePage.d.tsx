import { Fragment, type ReactNode, useEffect, useLayoutEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { FieldQuestionHandle } from "../components/node/FieldQuestion";
import type { MatchingQuestionHandle } from "../components/node/MatchingQuestion";
import type { MultiChoiceQuestionHandle } from "../components/node/MultiChoiceQuestion";
import type { RatingQuestionHandle } from "../components/node/RatingQuestion";
import type { RulesQuestionHandle } from "../components/node/RulesQuestion";
import { Input, Select, Button, ThemeToggle, Badge } from "../index.optimized";
import { FieldQuestion } from "../components/node/FieldQuestion";
import { MatchingQuestion } from "../components/node/MatchingQuestion";
import { MultiChoiceQuestion } from "../components/node/MultiChoiceQuestion";
import { RatingQuestion } from "../components/node/RatingQuestion";
import { RulesQuestion } from "../components/node/RulesQuestion";
import { savePreviewSurvey } from "../components/form_filler/previewStorage";
import type { QuestionContent, RuleContent, SurveyNode } from "../components/node/questionTypes";
import { serializeSurveyEntries, type SurveyEntry } from "../components/node/surveySerialize";
import { incrementQuestionId } from "../components/node/NodePillUtils";
import "./NodePage.css";

const DEBUG_SHOW_JSON = false;
const NODE_PAGE_STORAGE_KEY = "flowform.node-page.schema";
const NODE_PAGE_UI_STORAGE_KEY = "flowform.node-page.ui";

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
    setQuestions((current) => {
      return current.filter((q) => q.id !== id);
    });
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
      setCollapsedIds((current) => { const next = new Set(current); next.delete(question.id); return next; });
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
    <div className="node-page__add-question">
      <div className="node-page__add-question-head">
        <Badge variant="accent" size="sm">Build</Badge>
        <p className="node-page__add-question-label">Add another question</p>
        <p className="node-page__add-question-copy">
          Choose the next response format to keep building the flow.
        </p>
      </div>
      <div className="node-page__add-question-buttons">
        {QUESTION_TYPE_OPTIONS.map((option) => (
          <Button
            key={option.value}
            className="node-page__add-question-btn"
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
    <section className="node-page">
      <div className="node-page__toolbar">
        <div className="node-page__toolbar-shell">
          <div className="node-page__toolbar-header">
            <h4 className="node-page__toolbar-title">Search</h4>
            <Input
              className="node-page__toolbar-search-input"
              placeholder="Search by title or ID"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
            />
            <Select
              className="node-page__toolbar-filter"
              value={filterType}
              options={[
                { value: "all", label: "All question types" },
                ...QUESTION_TYPE_OPTIONS,
              ]}
              onChange={(event) => setFilterType(event.target.value as "all" | QuestionType)}
            />
          </div>
          <div className="node-page__toolbar-actions">
            <ThemeToggle />
            <Button
              className="node-page__toolbar-clear"
              type="button"
              variant="ghost"
              size="sm"
              onClick={clearSchema}
              disabled={questions.length === 0}
            >
              Clear
            </Button>
            <Button
              className="node-page__toolbar-preview"
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
      <div className="node-page__content">
        <div className="node-page__questions-stack">
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
                  <div className="node-page__divider" />
                )}

                {index === questions.length - 1 && (
                  <>
                    <div className="node-page__divider node-page__divider--section" />
                    {addQuestionCard}
                  </>
                )}
              </Fragment>
            )
          })}
          {questions.length === 0 && addQuestionCard}
        </div>
      </div>
      {DEBUG_SHOW_JSON && (
        <aside className="node-page__debug" aria-label="Debug survey JSON">
          <header className="node-page__debug-head">
            <span>Debug · survey JSON</span>
            <span className="node-page__debug-count">{questions.length} node{questions.length === 1 ? "" : "s"}</span>
          </header>
          <pre className="node-page__debug-body">{JSON.stringify(serializedSurvey, null, 2)}</pre>
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
      className={`node-page__question-wrapper ${isExpanded ? "" : "node-page__question-wrapper--collapsed"}`}
    >
      <div className="node-page__question-row">
        <Button
          className="node-page__question-collapse-btn"
          type="button"
          variant="ghost"
          size="xs"
          aria-label={isExpanded ? "Collapse question" : "Expand question"}
          aria-expanded={isExpanded}
          onClick={onToggleCollapse}
        >
          {isExpanded ? "▾" : "▸"}
        </Button>

        <div className="node-page__question-container">
          {children}
        </div>

        {isExpanded && isEditing && (
          <div className="node-page__question-move-controls" aria-label="Move question">
            <Button
              className="node-page__question-move-btn"
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
              className="node-page__question-move-btn"
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
