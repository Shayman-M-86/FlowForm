export type ControlSize = "xxs" | "xs" | "sm" | "md" | "lg" | "xl";
export type TextareaSize = "sm" | "md" | "lg";

export const controlSizeClasses: Record<ControlSize, string> = {
  xxs: "min-h-[26px] px-2 text-[0.75rem] leading-none",
  xs: "min-h-[30px] px-2.5 text-[0.8rem] leading-none",
  sm: "min-h-[34px] px-3 text-[0.86rem] leading-[1.2]",
  md: "min-h-10 px-4 text-sm leading-normal",
  lg: "min-h-11 px-5 text-base leading-normal",
  xl: "min-h-12 px-6 text-[1.05rem] leading-normal",
};

export const badgeSizeClasses: Record<ControlSize, string> = {
  xxs: "px-1.5 py-0.5 text-[0.65rem] leading-none",
  xs: "px-2 py-1 text-[0.72rem] leading-none",
  sm: "px-2.5 py-1 text-[0.8rem] leading-none",
  md: "px-3 py-1.5 text-xs leading-none",
  lg: "px-3.5 py-2 text-sm leading-none",
  xl: "px-4 py-2.5 text-sm leading-none",
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
  sm: "px-3 py-2 text-[0.86rem] leading-6",
  md: "px-4 py-3 text-sm leading-6",
  lg: "px-4 py-3 text-base leading-7",
};

export const textareaSizeClasses: Record<TextareaSize, string> = {
  sm: `min-h-[88px] max-h-[88px] ${textareaBodySizeClasses.sm}`,
  md: `min-h-[120px] max-h-[120px] ${textareaBodySizeClasses.md}`,
  lg: `min-h-[168px] max-h-[168px] ${textareaBodySizeClasses.lg}`,
};

export const textareaMinHeights: Record<TextareaSize, number> = {
  sm: 88,
  md: 120,
  lg: 168,
};
