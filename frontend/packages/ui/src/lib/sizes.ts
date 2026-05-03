export type ControlSize = "xxs" | "xs" | "sm" | "md" | "lg" | "xl";
export type TextareaSize = "sm" | "md" | "lg";

export const controlSizeClasses: Record<ControlSize, string> = {
  xxs: "ui-control-xxs",
  xs: "ui-control-xs",
  sm: "ui-control-sm",
  md: "ui-control-md",
  lg: "ui-control-lg",
  xl: "ui-control-xl",
};

export const badgeSizeClasses: Record<ControlSize, string> = {
  xxs: "ui-badge-xxs",
  xs: "ui-badge-xs",
  sm: "ui-badge-sm",
  md: "ui-badge-md",
  lg: "ui-badge-lg",
  xl: "ui-badge-xl",
};

export const cardPaddingClasses: Record<ControlSize, string> = {
  xxs: "p-1",
  xs: "p-2",
  sm: "p-3",
  md: "p-5",
  lg: "p-6",
  xl: "p-8",
};

export const stackGapClasses: Record<ControlSize, string> = {
  xxs: "gap-1",
  xs: "gap-2",
  sm: "gap-3",
  md: "gap-4",
  lg: "gap-6",
  xl: "gap-8",
};

export const textareaBodySizeClasses: Record<TextareaSize, string> = {
  sm: "ui-textarea-body-sm",
  md: "ui-textarea-body-md",
  lg: "ui-textarea-body-lg",
};

export const textareaSizeClasses: Record<TextareaSize, string> = {
  sm: "ui-textarea-sm",
  md: "ui-textarea-md",
  lg: "ui-textarea-lg",
};

export const textareaMinHeights: Record<TextareaSize, number> = {
  sm: 88,
  md: 120,
  lg: 168,
};

export const layoutGapClasses = {
  xs: "gap-2",
  sm: "gap-3",
  md: "gap-5",
  lg: "gap-6",
  xl: "gap-8",
} as const;

export type LayoutGap = keyof typeof layoutGapClasses;
