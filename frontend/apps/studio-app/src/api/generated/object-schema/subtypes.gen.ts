// This file is auto-generated — do not edit manually

import type { MatchingPairIn, NumericRangeScoreIn } from "./requests.gen";

export interface ChoiceOptionMapConfig {
  option_scores: Record<string, unknown>;
  combine: "sum" | "max";
}

export const ChoiceOptionMapConfigConstraints = {
  combine: { maxLength: 3 },
} as const;

export interface FieldNumericRangesConfig {
  ranges: NumericRangeScoreIn[];
}

export const FieldNumericRangesConfigConstraints = {
  ranges: { maxItems: 50 },
} as const;

export interface MatchingAnswerKeyConfig {
  correct_pairs: MatchingPairIn[];
  points_per_correct: number | number;
  penalty_per_incorrect: number | number;
  max_score: number | number | null;
}

export const MatchingAnswerKeyConfigConstraints = {
  correct_pairs: { maxItems: 50 },
} as const;

export interface RatingDirectConfig {
  multiplier: number | number;
}

export interface ChoiceAnswerValue {
  selected: string[];
}

export const ChoiceAnswerValueConstraints = {
  selected: { maxItems: 50 },
} as const;

export interface FieldAnswerValue {
  value: string | number | number | boolean | string | null;
}

export const FieldAnswerValueConstraints = {
  value: { maxLength: 5000 },
} as const;

export interface MatchPair {
  left_id: string;
  right_id: string;
}

export const MatchPairConstraints = {
  left_id: { maxLength: 128 },
  right_id: { maxLength: 128 },
} as const;

export interface MatchingAnswerValue {
  matches: MatchPair[];
}

export const MatchingAnswerValueConstraints = {
  matches: { maxItems: 50 },
} as const;

export interface RatingAnswerValue {
  value: number | number;
}
