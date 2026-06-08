import type {
  CreateQuestionNodeRequest,
  CreateRuleNodeRequest,
} from "@flowform/schema";
import { FieldQuestion, type FieldQuestionNode } from "../../components/node/QuestionNode/FieldQuestion";
import { MultiChoiceQuestion, type MultiChoiceQuestionNode } from "../../components/node/QuestionNode/MultiChoiceQuestion";
import { MatchingQuestion, type MatchingQuestionNode } from "../../components/node/QuestionNode/MatchingQuestion";
import { RatingQuestion, type RatingQuestionNode } from "../../components/node/QuestionNode/RatingQuestion";
import { RulesQuestion, type RulesQuestionNode } from "../../components/node/QuestionNode/rules/RulesQuestion";

type SurveyNode = CreateQuestionNodeRequest | CreateRuleNodeRequest;
type QuestionNode = CreateQuestionNodeRequest;

interface NodeRendererProps {
  node: SurveyNode;
  onChange: (next: SurveyNode) => void;
  onDelete: () => void;
  idError?: string;
  validationError?: string;
  isCollapsed: boolean;
  isEditMode: boolean;
  onExpand: () => void;
  onExpandInEditMode: () => void;
  onEditModeChange: (isEditMode: boolean) => void;
  previousSiblings?: QuestionNode[];
  followingSiblings?: QuestionNode[];
}

/**
 * Routing layer: pick the correct pill for a node. The generated node already
 * tells us the type — node_type for rules, content.family for questions — so
 * there is no separate manual type field. Each branch narrows the node to the
 * pill's own node contract (a discriminated subtype of SurveyNode).
 */
export function NodeRenderer({
  node,
  onChange,
  previousSiblings,
  followingSiblings,
  ...shared
}: NodeRendererProps) {
  if (node.node_type === "rule") {
    return (
      <RulesQuestion
        node={node as RulesQuestionNode}
        onChange={onChange as (next: RulesQuestionNode) => void}
        previousSiblings={previousSiblings}
        followingSiblings={followingSiblings}
        {...shared}
      />
    );
  }

  switch (node.content.family) {
    case "choice":
      return (
        <MultiChoiceQuestion
          node={node as MultiChoiceQuestionNode}
          onChange={onChange as (next: MultiChoiceQuestionNode) => void}
          {...shared}
        />
      );
    case "matching":
      return (
        <MatchingQuestion
          node={node as MatchingQuestionNode}
          onChange={onChange as (next: MatchingQuestionNode) => void}
          {...shared}
        />
      );
    case "rating":
      return (
        <RatingQuestion
          node={node as RatingQuestionNode}
          onChange={onChange as (next: RatingQuestionNode) => void}
          {...shared}
        />
      );
    case "field":
      return (
        <FieldQuestion
          node={node as FieldQuestionNode}
          onChange={onChange as (next: FieldQuestionNode) => void}
          {...shared}
        />
      );
  }
}
