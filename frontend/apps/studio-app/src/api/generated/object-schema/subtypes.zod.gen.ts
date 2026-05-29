// This file is auto-generated — do not edit manually

import { z } from "zod";

import { zMatchingPairIn, zNumericRangeScoreIn } from "./requests.zod.gen";

export const zChoiceOptionMapConfig = z.object({
  option_scores: z.record(z.string(), z.unknown()),
  combine: z.union([z.literal("sum"), z.literal("max")]),
});

export const zFieldNumericRangesConfig = z.object({
  ranges: z.array(zNumericRangeScoreIn).max(50),
});

export const zMatchingAnswerKeyConfig = z.object({
  correct_pairs: z.array(zMatchingPairIn).max(50),
  points_per_correct: z.union([z.number().int(), z.number()]),
  penalty_per_incorrect: z.union([z.number().int(), z.number()]),
  max_score: z.union([z.number().int(), z.number()]).nullable(),
});

export const zRatingDirectConfig = z.object({
  multiplier: z.union([z.number().int(), z.number()]),
});

export const zChoiceAnswerValue = z.object({
  selected: z.array(z.string().max(128)).max(50),
});

export const zFieldAnswerValue = z.object({
  value: z.union([z.string().max(5000), z.number().int(), z.number(), z.boolean(), z.string().max(10)]).nullable(),
});

export const zMatchPair = z.object({
  left_id: z.string().max(128),
  right_id: z.string().max(128),
});

export const zMatchingAnswerValue = z.object({
  matches: z.array(zMatchPair).max(50),
});

export const zRatingAnswerValue = z.object({
  value: z.union([z.number().int(), z.number()]),
});
