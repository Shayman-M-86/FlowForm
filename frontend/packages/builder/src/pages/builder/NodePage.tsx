import {
  Fragment,
  type ReactNode,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Badge, Button } from "@flowform/ui";
import type {
  CreateQuestionNodeRequest,
  CreateRuleNodeRequest,
} from "@flowform/schema";
import { NodePillMobileControlsProvider } from "../../components/node/NodePillShell";
import { PlusGridAnimation } from "../../components/node/PlusGridAnimation";
import { NodeRenderer } from "./NodeRenderer";
import { createDefaultNode, type NodeKind } from "./nodeFactories";
import {
  computeNextNodeKey,
  findDuplicateNodeKeyIds,
  getNextSortKey,
  moveNode,
} from "./nodeOrdering";
import { buildRuleSiblings } from "./ruleRelationships";

type SurveyNode = CreateQuestionNodeRequest | CreateRuleNodeRequest;

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

const QUESTION_TYPE_OPTIONS: Array<{ value: NodeKind; label: string }> = [
  { value: "choice", label: "Multiple choice" },
  { value: "matching", label: "Matching" },
  { value: "rating", label: "Rating" },
  { value: "field", label: "Field" },
  { value: "rule", label: "Rules" },
];

const SWAP_ANIMATION_MS = 280;

interface NodePageProps {
  nodes: SurveyNode[];
  disabled?: boolean;
  onNodesChange: (nodes: SurveyNode[]) => void;
}

export function NodePage({ nodes, disabled = false, onNodesChange }: NodePageProps) {
  // Presentation-only state, keyed by the stable node id. None of this touches
  // the survey schema — the nodes prop is the single source of truth.
  const [collapsedIds, setCollapsedIds] = useState<Set<number>>(() => new Set());
  const [editingIds, setEditingIds] = useState<Set<number>>(() => new Set());

  const questionWrapperNodeMap = useRef<Map<number, HTMLDivElement>>(new Map());
  const pendingMoveAnimation = useRef<{
    positions: Map<number, number>;
    movedId: number;
  } | null>(null);
  const newlyAddedNodeId = useRef<number | null>(null);

  const duplicateIds = useMemo(() => findDuplicateNodeKeyIds(nodes), [nodes]);

  // RulesQuestion uses sibling content to show branching targets. Build entries
  // only for rules so ordinary question rows do not pay for unused slices.
  const siblingsMap = useMemo(() => buildRuleSiblings(nodes), [nodes]);

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

    nodes.forEach((node) => {
      const questionNode = questionWrapperNodeMap.current.get(node.id);
      const previousTop = pendingAnimation.positions.get(node.id);
      if (!questionNode || previousTop === undefined) return;

      const nextTop = questionNode.getBoundingClientRect().top;
      const deltaY = previousTop - nextTop;

      questionNode.style.position = "relative";
      questionNode.style.zIndex = node.id === pendingAnimation.movedId ? "3" : "1";

      const questionContainer = questionNode.querySelector<HTMLDivElement>(".node-page__question-container");
      if (questionContainer && node.id === pendingAnimation.movedId) {
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
  }, [nodes]);

  useEffect(() => {
    const addedId = newlyAddedNodeId.current;
    if (addedId === null) return;

    newlyAddedNodeId.current = null;
    const node = questionWrapperNodeMap.current.get(addedId);
    if (node) {
      node.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [nodes]);

  const updateNode = useCallback((next: SurveyNode) => {
    onNodesChange(nodes.map((node) => (node.id === next.id ? next : node)));
  }, [nodes, onNodesChange]);

  const removeNode = useCallback((id: number) => {
    onNodesChange(nodes.filter((node) => node.id !== id));
    setEditingIds((current) => {
      if (!current.has(id)) return current;
      const next = new Set(current);
      next.delete(id);
      return next;
    });
    setCollapsedIds((current) => {
      if (!current.has(id)) return current;
      const next = new Set(current);
      next.delete(id);
      return next;
    });
    questionWrapperNodeMap.current.delete(id);
  }, [nodes, onNodesChange]);

  const addNode = useCallback((kind: NodeKind) => {
    const node = createDefaultNode(kind, getNextSortKey(nodes), computeNextNodeKey(nodes, kind));
    newlyAddedNodeId.current = node.id;
    onNodesChange([...nodes, node]);
    setEditingIds((current) => {
      const next = new Set(current);
      next.add(node.id);
      return next;
    });
  }, [nodes, onNodesChange]);

  const handleMove = useCallback((id: number, direction: "up" | "down") => {
    pendingMoveAnimation.current = {
      positions: new Map(
        nodes.map((node) => [
          node.id,
          questionWrapperNodeMap.current.get(node.id)?.getBoundingClientRect().top ?? 0,
        ]),
      ),
      movedId: id,
    };
    onNodesChange(moveNode(nodes, id, direction));
  }, [nodes, onNodesChange]);

  function setEditMode(id: number, isEditMode: boolean) {
    setEditingIds((current) => {
      const next = new Set(current);
      if (isEditMode) {
        next.add(id);
      } else {
        next.delete(id);
      }
      return next;
    });
  }

  function expand(id: number) {
    setCollapsedIds((current) => {
      if (!current.has(id)) return current;
      const next = new Set(current);
      next.delete(id);
      return next;
    });
  }

  function expandInEditMode(id: number) {
    expand(id);
    setEditMode(id, true);
  }

  function toggleCollapsed(id: number) {
    setCollapsedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
        setEditingIds((editing) => {
          if (!editing.has(id)) return editing;
          const nextEditing = new Set(editing);
          nextEditing.delete(id);
          return nextEditing;
        });
      }
      return next;
    });
  }

  const isExpanded = (node: SurveyNode) => !collapsedIds.has(node.id);

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
            disabled={disabled}
            onClick={() => addNode(option.value)}
          >
            <span aria-hidden="true">+</span>
            {option.label}
          </Button>
        ))}
      </div>
    </div>
  ), [addNode, disabled]);

  return (
    <section className="node-page relative isolate flex min-h-full flex-col mt-0.5 overflow-x-clip">
      <style dangerouslySetInnerHTML={{ __html: NODE_PAGE_STYLES }} />
      <PlusGridAnimation />
      <div className="node-page__content relative z-10 box-border flex w-full max-w-[calc(980px+(var(--node-page-controls-gutter)*2))] shrink-0 flex-col items-center self-center px-[var(--node-page-controls-gutter)] pb-10 pt-(--node-page-toolbar-gap) max-[640px]:gap-[14px] max-[640px]:px-5 max-[640px]:pt-[calc(var(--node-page-toolbar-gap)+10px)]">
        <div className="node-page__questions-stack flex w-full flex-col gap-5">
          {nodes.map((node, index) => {
            const nextNode = nodes[index + 1];
            const shouldShowDivider =
              index < nodes.length - 1 &&
              (isExpanded(node) || (nextNode ? isExpanded(nextNode) : false));
            const siblings = siblingsMap.get(node.id);

            return (
              <Fragment key={node.id}>
                <QuestionRow
                  index={index}
                  isLast={index === nodes.length - 1}
                  isEditing={editingIds.has(node.id)}
                  isExpanded={isExpanded(node)}
                  disabled={disabled}
                  onToggleCollapse={() => toggleCollapsed(node.id)}
                  onMoveUp={() => handleMove(node.id, "up")}
                  onMoveDown={() => handleMove(node.id, "down")}
                  onSetWrapperNode={(wrapper) => {
                    if (wrapper) {
                      questionWrapperNodeMap.current.set(node.id, wrapper);
                    } else {
                      questionWrapperNodeMap.current.delete(node.id);
                    }
                  }}
                >
                  <NodeRenderer
                    node={node}
                    onChange={updateNode}
                    onDelete={() => removeNode(node.id)}
                    idError={duplicateIds.has(node.id) ? "ID must be unique." : undefined}
                    isCollapsed={collapsedIds.has(node.id)}
                    isEditMode={editingIds.has(node.id)}
                    onExpand={() => expand(node.id)}
                    onExpandInEditMode={() => expandInEditMode(node.id)}
                    onEditModeChange={(isEditMode) => setEditMode(node.id, isEditMode)}
                    previousSiblings={siblings?.previous ?? []}
                    followingSiblings={siblings?.following ?? []}
                  />
                </QuestionRow>

                {shouldShowDivider && (
                  <div className="my-2 h-px bg-border" />
                )}

                {index === nodes.length - 1 && (
                  <>
                    <div className="node-page__section-divider my-2 h-px bg-border" />
                    {addQuestionCard}
                  </>
                )}
              </Fragment>
            );
          })}
          {nodes.length === 0 && addQuestionCard}
        </div>
      </div>
    </section>
  );
}

function QuestionRow({
  index,
  isLast,
  isEditing,
  isExpanded,
  disabled,
  onToggleCollapse,
  onMoveUp,
  onMoveDown,
  onSetWrapperNode,
  children,
}: {
  index: number;
  isLast: boolean;
  isEditing: boolean;
  isExpanded: boolean;
  disabled: boolean;
  onToggleCollapse: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
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
                      disabled={disabled || index === 0}
                      aria-label="Move question up"
                      onClick={onMoveUp}
                    >
                      ↑
                    </Button>
                    <Button
                      className="min-h-[30px] min-w-[30px] p-0"
                      type="button"
                      variant="ghost"
                      size="sm"
                      disabled={disabled || isLast}
                      aria-label="Move question down"
                      onClick={onMoveDown}
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
              disabled={disabled || index === 0}
              aria-label="Move question up"
              onClick={onMoveUp}
            >
              ↑
            </Button>
            <Button
              className="min-w-[34px] p-0"
              type="button"
              variant="ghost"
              size="xs"
              disabled={disabled || isLast}
              aria-label="Move question down"
              onClick={onMoveDown}
            >
              ↓
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
