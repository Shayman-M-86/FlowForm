// This file is auto-generated — do not edit manually
export const surveyNodeImportJsonSchema = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "array",
  "minItems": 1,
  "maxItems": 500,
  "items": {
    "oneOf": [
      {
        "$ref": "#/$defs/CreateQuestionNodeRequest"
      },
      {
        "$ref": "#/$defs/CreateRuleNodeRequest"
      }
    ]
  },
  "$defs": {
    "ChoiceConditionIn": {
      "additionalProperties": false,
      "description": "Represents a condition block targeting a choice question.",
      "properties": {
        "target_id": {
          "maxLength": 128,
          "minLength": 1,
          "title": "Target Id",
          "type": "string"
        },
        "family": {
          "const": "choice",
          "title": "Family",
          "type": "string",
          "maxLength": 6
        },
        "requirements": {
          "$ref": "#/$defs/ChoiceRequirementsIn"
        }
      },
      "required": [
        "target_id",
        "family",
        "requirements"
      ],
      "title": "ChoiceConditionIn",
      "type": "object"
    },
    "ChoiceDefinitionIn": {
      "additionalProperties": false,
      "description": "definition block for a choice question.",
      "properties": {
        "min": {
          "minimum": 0,
          "title": "Min",
          "type": "integer"
        },
        "max": {
          "minimum": 1,
          "title": "Max",
          "type": "integer"
        },
        "options": {
          "items": {
            "$ref": "#/$defs/ChoiceOptionIn"
          },
          "maxItems": 10,
          "title": "Options",
          "type": "array"
        }
      },
      "required": [
        "min",
        "max",
        "options"
      ],
      "title": "ChoiceDefinitionIn",
      "type": "object"
    },
    "ChoiceOptionIn": {
      "additionalProperties": false,
      "description": "A single selectable option for a choice question.",
      "properties": {
        "id": {
          "maxLength": 128,
          "minLength": 1,
          "title": "Id",
          "type": "string"
        },
        "label": {
          "maxLength": 1000,
          "minLength": 1,
          "title": "Label",
          "type": "string"
        }
      },
      "required": [
        "id",
        "label"
      ],
      "title": "ChoiceOptionIn",
      "type": "object"
    },
    "ChoiceQuestionSchemaIn": {
      "additionalProperties": false,
      "description": "Incoming choice-question content schema.",
      "properties": {
        "family": {
          "const": "choice",
          "title": "Family",
          "type": "string",
          "maxLength": 6
        },
        "label": {
          "maxLength": 1000,
          "minLength": 1,
          "title": "Label",
          "type": "string"
        },
        "title": {
          "anyOf": [
            {
              "maxLength": 500,
              "minLength": 0,
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Title"
        },
        "definition": {
          "$ref": "#/$defs/ChoiceDefinitionIn"
        }
      },
      "required": [
        "family",
        "label",
        "definition"
      ],
      "title": "ChoiceQuestionSchemaIn",
      "type": "object",
      "x-flowform-export": "builder"
    },
    "ChoiceRequirementsIn": {
      "additionalProperties": false,
      "description": "Validation requirements for a choice-question condition.",
      "properties": {
        "required": {
          "items": {
            "maxLength": 128,
            "minLength": 1,
            "type": "string"
          },
          "maxItems": 50,
          "title": "Required",
          "type": "array"
        },
        "forbidden": {
          "items": {
            "maxLength": 128,
            "minLength": 1,
            "type": "string"
          },
          "maxItems": 50,
          "title": "Forbidden",
          "type": "array"
        },
        "any_of": {
          "items": {
            "maxLength": 128,
            "minLength": 1,
            "type": "string"
          },
          "maxItems": 50,
          "title": "Any Of",
          "type": "array"
        }
      },
      "title": "ChoiceRequirementsIn",
      "type": "object"
    },
    "CreateQuestionNodeRequest": {
      "additionalProperties": false,
      "description": "Validates requests that create a new question node.",
      "properties": {
        "id": {
          "format": "uuid",
          "title": "Id",
          "type": "string",
          "maxLength": 36
        },
        "node_key": {
          "maxLength": 128,
          "minLength": 1,
          "title": "Node Key",
          "type": "string"
        },
        "node_type": {
          "const": "question",
          "title": "Node Type",
          "type": "string",
          "maxLength": 8
        },
        "sort_key": {
          "exclusiveMinimum": 0,
          "title": "Sort Key",
          "type": "integer"
        },
        "content": {
          "discriminator": {
            "mapping": {
              "choice": "#/$defs/ChoiceQuestionSchemaIn",
              "field": "#/$defs/FieldQuestionSchemaIn",
              "matching": "#/$defs/MatchingQuestionSchemaIn",
              "rating": "#/$defs/RatingQuestionSchemaIn"
            },
            "propertyName": "family"
          },
          "oneOf": [
            {
              "$ref": "#/$defs/ChoiceQuestionSchemaIn"
            },
            {
              "$ref": "#/$defs/FieldQuestionSchemaIn"
            },
            {
              "$ref": "#/$defs/MatchingQuestionSchemaIn"
            },
            {
              "$ref": "#/$defs/RatingQuestionSchemaIn"
            }
          ],
          "title": "Content"
        }
      },
      "required": [
        "id",
        "node_key",
        "node_type",
        "sort_key",
        "content"
      ],
      "title": "CreateQuestionNodeRequest",
      "type": "object",
      "x-flowform-export": "builder"
    },
    "CreateRuleNodeRequest": {
      "additionalProperties": false,
      "description": "Validates requests that create a new rule node.",
      "properties": {
        "id": {
          "format": "uuid",
          "title": "Id",
          "type": "string",
          "maxLength": 36
        },
        "node_key": {
          "maxLength": 128,
          "minLength": 1,
          "title": "Node Key",
          "type": "string"
        },
        "node_type": {
          "const": "rule",
          "title": "Node Type",
          "type": "string",
          "maxLength": 4
        },
        "sort_key": {
          "exclusiveMinimum": 0,
          "title": "Sort Key",
          "type": "integer"
        },
        "content": {
          "$ref": "#/$defs/RuleSchemaIn"
        }
      },
      "required": [
        "id",
        "node_key",
        "node_type",
        "sort_key",
        "content"
      ],
      "title": "CreateRuleNodeRequest",
      "type": "object",
      "x-flowform-export": "builder"
    },
    "DateFieldRequirementsIn": {
      "additionalProperties": false,
      "description": "Validation requirements for a date field-question condition.",
      "properties": {
        "type": {
          "const": "date",
          "title": "Type",
          "type": "string",
          "maxLength": 4
        },
        "operator": {
          "enum": [
            "before",
            "after"
          ],
          "title": "Operator",
          "type": "string",
          "maxLength": 6
        },
        "value": {
          "maxLength": 10,
          "title": "Value",
          "type": "string"
        }
      },
      "required": [
        "type",
        "operator",
        "value"
      ],
      "title": "DateFieldRequirementsIn",
      "type": "object"
    },
    "EndAndDiscardActionIn": {
      "additionalProperties": false,
      "description": "Navigation action that ends the survey and discards the response.",
      "properties": {
        "end_and_discard": {
          "default": true,
          "title": "End And Discard",
          "type": "boolean"
        }
      },
      "title": "EndAndDiscardActionIn",
      "type": "object"
    },
    "EndAndSubmitActionIn": {
      "additionalProperties": false,
      "description": "Navigation action that ends the survey and submits the response.",
      "properties": {
        "end_and_submit": {
          "default": true,
          "title": "End And Submit",
          "type": "boolean"
        }
      },
      "title": "EndAndSubmitActionIn",
      "type": "object"
    },
    "FieldConditionIn": {
      "additionalProperties": false,
      "description": "Represents a condition block targeting a field question.",
      "properties": {
        "target_id": {
          "maxLength": 128,
          "minLength": 1,
          "title": "Target Id",
          "type": "string"
        },
        "family": {
          "const": "field",
          "title": "Family",
          "type": "string",
          "maxLength": 5
        },
        "requirements": {
          "discriminator": {
            "mapping": {
              "date": "#/$defs/DateFieldRequirementsIn",
              "number": "#/$defs/NumberFieldRequirementsIn"
            },
            "propertyName": "type"
          },
          "oneOf": [
            {
              "$ref": "#/$defs/NumberFieldRequirementsIn"
            },
            {
              "$ref": "#/$defs/DateFieldRequirementsIn"
            }
          ],
          "title": "Requirements"
        }
      },
      "required": [
        "target_id",
        "family",
        "requirements"
      ],
      "title": "FieldConditionIn",
      "type": "object"
    },
    "FieldDefinitionIn": {
      "additionalProperties": false,
      "description": "definition block for a field question.",
      "properties": {
        "field_type": {
          "enum": [
            "short_text",
            "long_text",
            "email",
            "number",
            "date",
            "phone"
          ],
          "title": "Field Type",
          "type": "string",
          "maxLength": 10
        },
        "ui": {
          "$ref": "#/$defs/FieldUIIn"
        }
      },
      "required": [
        "field_type"
      ],
      "title": "FieldDefinitionIn",
      "type": "object"
    },
    "FieldQuestionSchemaIn": {
      "additionalProperties": false,
      "description": "Incoming field-question content schema.",
      "properties": {
        "family": {
          "const": "field",
          "title": "Family",
          "type": "string",
          "maxLength": 5
        },
        "label": {
          "maxLength": 1000,
          "minLength": 1,
          "title": "Label",
          "type": "string"
        },
        "title": {
          "anyOf": [
            {
              "maxLength": 500,
              "minLength": 0,
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Title"
        },
        "definition": {
          "$ref": "#/$defs/FieldDefinitionIn"
        }
      },
      "required": [
        "family",
        "label",
        "definition"
      ],
      "title": "FieldQuestionSchemaIn",
      "type": "object",
      "x-flowform-export": "builder"
    },
    "FieldUIIn": {
      "additionalProperties": false,
      "description": "UI block for a field question.",
      "properties": {
        "placeholder": {
          "default": "",
          "maxLength": 50,
          "title": "Placeholder",
          "type": "string"
        }
      },
      "title": "FieldUIIn",
      "type": "object"
    },
    "MatchingConditionIn": {
      "additionalProperties": false,
      "description": "Represents a condition block targeting a matching question.",
      "properties": {
        "target_id": {
          "maxLength": 128,
          "minLength": 1,
          "title": "Target Id",
          "type": "string"
        },
        "family": {
          "const": "matching",
          "title": "Family",
          "type": "string",
          "maxLength": 8
        },
        "requirements": {
          "$ref": "#/$defs/MatchingRequirementsIn"
        }
      },
      "required": [
        "target_id",
        "family",
        "requirements"
      ],
      "title": "MatchingConditionIn",
      "type": "object"
    },
    "MatchingDefinitionIn": {
      "additionalProperties": false,
      "description": "definition block for a matching question.",
      "properties": {
        "prompts": {
          "items": {
            "$ref": "#/$defs/MatchingItemIn"
          },
          "maxItems": 10,
          "title": "Prompts",
          "type": "array"
        },
        "matches": {
          "items": {
            "$ref": "#/$defs/MatchingItemIn"
          },
          "maxItems": 10,
          "title": "Matches",
          "type": "array"
        }
      },
      "required": [
        "prompts",
        "matches"
      ],
      "title": "MatchingDefinitionIn",
      "type": "object"
    },
    "MatchingItemIn": {
      "additionalProperties": false,
      "description": "One item on either side of a matching question.",
      "properties": {
        "id": {
          "maxLength": 128,
          "minLength": 1,
          "title": "Id",
          "type": "string"
        },
        "label": {
          "maxLength": 250,
          "minLength": 1,
          "title": "Label",
          "type": "string"
        }
      },
      "required": [
        "id",
        "label"
      ],
      "title": "MatchingItemIn",
      "type": "object"
    },
    "MatchingPairIn": {
      "additionalProperties": false,
      "description": "A single prompt-to-match pairing in a matching condition.",
      "properties": {
        "prompt_id": {
          "maxLength": 128,
          "minLength": 1,
          "title": "Prompt Id",
          "type": "string"
        },
        "match_id": {
          "maxLength": 128,
          "minLength": 1,
          "title": "Match Id",
          "type": "string"
        }
      },
      "required": [
        "prompt_id",
        "match_id"
      ],
      "title": "MatchingPairIn",
      "type": "object"
    },
    "MatchingQuestionSchemaIn": {
      "additionalProperties": false,
      "description": "Incoming matching-question content schema.",
      "properties": {
        "family": {
          "const": "matching",
          "title": "Family",
          "type": "string",
          "maxLength": 8
        },
        "label": {
          "maxLength": 1000,
          "minLength": 1,
          "title": "Label",
          "type": "string"
        },
        "title": {
          "anyOf": [
            {
              "maxLength": 500,
              "minLength": 0,
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Title"
        },
        "definition": {
          "$ref": "#/$defs/MatchingDefinitionIn"
        }
      },
      "required": [
        "family",
        "label",
        "definition"
      ],
      "title": "MatchingQuestionSchemaIn",
      "type": "object",
      "x-flowform-export": "builder"
    },
    "MatchingRequirementsIn": {
      "additionalProperties": false,
      "description": "Validation requirements for a matching-question condition.",
      "properties": {
        "required": {
          "items": {
            "$ref": "#/$defs/MatchingPairIn"
          },
          "maxItems": 50,
          "minItems": 1,
          "title": "Required",
          "type": "array"
        }
      },
      "required": [
        "required"
      ],
      "title": "MatchingRequirementsIn",
      "type": "object"
    },
    "NumberFieldRequirementsIn": {
      "additionalProperties": false,
      "description": "Validation requirements for a numeric field-question condition.",
      "properties": {
        "type": {
          "const": "number",
          "title": "Type",
          "type": "string",
          "maxLength": 6
        },
        "operator": {
          "enum": [
            "LT",
            "LTE",
            "GT",
            "GTE",
            "EQ",
            "NEQ"
          ],
          "title": "Operator",
          "type": "string",
          "maxLength": 3
        },
        "value": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "number"
            }
          ],
          "title": "Value"
        }
      },
      "required": [
        "type",
        "operator",
        "value"
      ],
      "title": "NumberFieldRequirementsIn",
      "type": "object"
    },
    "RatingConditionIn": {
      "additionalProperties": false,
      "description": "Represents a condition block targeting a rating question.",
      "properties": {
        "target_id": {
          "maxLength": 128,
          "minLength": 1,
          "title": "Target Id",
          "type": "string"
        },
        "family": {
          "const": "rating",
          "title": "Family",
          "type": "string",
          "maxLength": 6
        },
        "requirements": {
          "$ref": "#/$defs/RatingRequirementsIn"
        }
      },
      "required": [
        "target_id",
        "family",
        "requirements"
      ],
      "title": "RatingConditionIn",
      "type": "object"
    },
    "RatingEmojiDefinitionIn": {
      "additionalProperties": false,
      "description": "definition block for an emoji-style rating question.",
      "properties": {
        "variant": {
          "const": "emoji",
          "title": "Variant",
          "type": "string",
          "maxLength": 5
        },
        "emoji_list": {
          "enum": [
            "sad_to_happy",
            "angry_to_happy",
            "disgust_to_happy"
          ],
          "title": "Emoji List",
          "type": "string",
          "maxLength": 16
        },
        "words": {
          "default": false,
          "title": "Words",
          "type": "boolean"
        },
        "ui": {
          "$ref": "#/$defs/RatingUIIn"
        }
      },
      "required": [
        "variant",
        "emoji_list",
        "ui"
      ],
      "title": "RatingEmojiDefinitionIn",
      "type": "object"
    },
    "RatingQuestionSchemaIn": {
      "additionalProperties": false,
      "description": "Incoming rating-question content schema.",
      "properties": {
        "family": {
          "const": "rating",
          "title": "Family",
          "type": "string",
          "maxLength": 6
        },
        "label": {
          "maxLength": 1000,
          "minLength": 1,
          "title": "Label",
          "type": "string"
        },
        "title": {
          "anyOf": [
            {
              "maxLength": 500,
              "minLength": 0,
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Title"
        },
        "definition": {
          "discriminator": {
            "mapping": {
              "emoji": "#/$defs/RatingEmojiDefinitionIn",
              "slider": "#/$defs/RatingSliderDefinitionIn",
              "stars": "#/$defs/RatingStarDefinitionIn"
            },
            "propertyName": "variant"
          },
          "oneOf": [
            {
              "$ref": "#/$defs/RatingSliderDefinitionIn"
            },
            {
              "$ref": "#/$defs/RatingStarDefinitionIn"
            },
            {
              "$ref": "#/$defs/RatingEmojiDefinitionIn"
            }
          ],
          "title": "Definition"
        }
      },
      "required": [
        "family",
        "label",
        "definition"
      ],
      "title": "RatingQuestionSchemaIn",
      "type": "object",
      "x-flowform-export": "builder"
    },
    "RatingRangeIn": {
      "additionalProperties": false,
      "description": "Range block for a slider rating — min, max, and step in one object.",
      "properties": {
        "min": {
          "maximum": 1000,
          "minimum": -1000,
          "title": "Min",
          "type": "number"
        },
        "max": {
          "maximum": 1000,
          "minimum": -1000,
          "title": "Max",
          "type": "number"
        },
        "step": {
          "exclusiveMinimum": 0,
          "title": "Step",
          "type": "number"
        }
      },
      "required": [
        "min",
        "max",
        "step"
      ],
      "title": "RatingRangeIn",
      "type": "object"
    },
    "RatingRequirementsIn": {
      "additionalProperties": false,
      "description": "Validation requirements for a rating-question condition.",
      "properties": {
        "min": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Min"
        },
        "max": {
          "anyOf": [
            {
              "type": "integer"
            },
            {
              "type": "number"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Max"
        }
      },
      "title": "RatingRequirementsIn",
      "type": "object"
    },
    "RatingSliderDefinitionIn": {
      "additionalProperties": false,
      "description": "definition block for a slider-style rating question.",
      "properties": {
        "variant": {
          "const": "slider",
          "title": "Variant",
          "type": "string",
          "maxLength": 6
        },
        "range": {
          "$ref": "#/$defs/RatingRangeIn"
        },
        "ui": {
          "$ref": "#/$defs/RatingUIIn"
        }
      },
      "required": [
        "variant",
        "range",
        "ui"
      ],
      "title": "RatingSliderDefinitionIn",
      "type": "object"
    },
    "RatingStarDefinitionIn": {
      "additionalProperties": false,
      "description": "definition block for a star-style rating question.",
      "properties": {
        "variant": {
          "const": "stars",
          "title": "Variant",
          "type": "string",
          "maxLength": 5
        },
        "stars": {
          "maximum": 12,
          "minimum": 1,
          "title": "Stars",
          "type": "integer"
        },
        "ui": {
          "$ref": "#/$defs/RatingUIIn"
        }
      },
      "required": [
        "variant",
        "stars",
        "ui"
      ],
      "title": "RatingStarDefinitionIn",
      "type": "object"
    },
    "RatingUIIn": {
      "additionalProperties": false,
      "description": "Left/right labels for all rating variants.",
      "properties": {
        "left_label": {
          "maxLength": 50,
          "minLength": 1,
          "title": "Left Label",
          "type": "string"
        },
        "right_label": {
          "maxLength": 50,
          "minLength": 1,
          "title": "Right Label",
          "type": "string"
        }
      },
      "required": [
        "left_label",
        "right_label"
      ],
      "title": "RatingUIIn",
      "type": "object"
    },
    "RuleBranchIn": {
      "additionalProperties": false,
      "description": "Represents the effects applied by a then or else branch.",
      "properties": {
        "set": {
          "anyOf": [
            {
              "items": {
                "$ref": "#/$defs/RuleSetItemIn"
              },
              "maxItems": 50,
              "minItems": 1,
              "type": "array"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Set"
        },
        "do": {
          "anyOf": [
            {
              "$ref": "#/$defs/SkipToActionIn"
            },
            {
              "$ref": "#/$defs/EndAndSubmitActionIn"
            },
            {
              "$ref": "#/$defs/EndAndDiscardActionIn"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Do"
        }
      },
      "title": "RuleBranchIn",
      "type": "object"
    },
    "RuleIfIn": {
      "additionalProperties": false,
      "description": "Represents the rule predicate and how its conditions are matched.",
      "properties": {
        "match": {
          "enum": [
            "ALL",
            "ANY",
            "NONE"
          ],
          "title": "Match",
          "type": "string",
          "maxLength": 4
        },
        "conditions": {
          "items": {
            "discriminator": {
              "mapping": {
                "choice": "#/$defs/ChoiceConditionIn",
                "field": "#/$defs/FieldConditionIn",
                "matching": "#/$defs/MatchingConditionIn",
                "rating": "#/$defs/RatingConditionIn"
              },
              "propertyName": "family"
            },
            "oneOf": [
              {
                "$ref": "#/$defs/ChoiceConditionIn"
              },
              {
                "$ref": "#/$defs/MatchingConditionIn"
              },
              {
                "$ref": "#/$defs/RatingConditionIn"
              },
              {
                "$ref": "#/$defs/FieldConditionIn"
              }
            ]
          },
          "maxItems": 50,
          "minItems": 1,
          "title": "Conditions",
          "type": "array"
        }
      },
      "required": [
        "match",
        "conditions"
      ],
      "title": "RuleIfIn",
      "type": "object"
    },
    "RuleSchemaIn": {
      "additionalProperties": false,
      "description": "Represents the full rule content stored in question_schema for a rule node.",
      "properties": {
        "if": {
          "$ref": "#/$defs/RuleIfIn"
        },
        "then": {
          "$ref": "#/$defs/RuleBranchIn"
        },
        "else": {
          "anyOf": [
            {
              "$ref": "#/$defs/RuleBranchIn"
            },
            {
              "type": "null"
            }
          ],
          "default": null
        }
      },
      "required": [
        "if",
        "then"
      ],
      "title": "RuleSchemaIn",
      "type": "object"
    },
    "RuleSetItemIn": {
      "additionalProperties": false,
      "description": "Represents one visibility or required-state change applied by a branch.",
      "properties": {
        "target_id": {
          "maxLength": 128,
          "minLength": 1,
          "title": "Target Id",
          "type": "string"
        },
        "visible": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Visible"
        },
        "required": {
          "anyOf": [
            {
              "type": "boolean"
            },
            {
              "type": "null"
            }
          ],
          "default": null,
          "title": "Required"
        }
      },
      "required": [
        "target_id"
      ],
      "title": "RuleSetItemIn",
      "type": "object"
    },
    "SkipToActionIn": {
      "additionalProperties": false,
      "description": "Navigation action that jumps to a specific question.",
      "properties": {
        "skip_to": {
          "maxLength": 128,
          "minLength": 1,
          "title": "Skip To",
          "type": "string"
        }
      },
      "required": [
        "skip_to"
      ],
      "title": "SkipToActionIn",
      "type": "object"
    }
  }
} as const;
