export const nodePillShellClass = [
  "flex w-full min-h-[360px] flex-col overflow-hidden rounded-2xl border border-border bg-card text-card-foreground shadow-sm",
  "transition-colors",
].join(" ");

export const nodePillShellEditClass = [
  "border-accent ring-1 ring-accent",
  "max-[640px]:-mx-5 max-[640px]:w-[calc(100%+2.5rem)] max-[640px]:rounded-none max-[640px]:border-x-0 max-[640px]:shadow-none",
].join(" ");

export const nodePillCollapsedShellClass =
  "flex flex-col rounded-2xl border border-border bg-card";

export const nodePillTopbarClass =
  "flex w-full flex-wrap items-center border-b border-border bg-muted/50 [background-image:var(--node-pill-topbar-gradient)] gap-3 px-3.5 py-3.5";

export const nodePillBodyClass = "flex flex-1 flex-col gap-4 p-5";

export const nodePillFieldClass = "flex flex-col gap-2.5";

export const nodePillFieldHeadClass =
  "flex items-center justify-between gap-2";

export const nodePillLabelClass =
  "text-[1.4rem] font-semibold text-muted-foreground";

export const nodePillSubLabelClass =
  "text-[0.78rem] font-semibold uppercase tracking-[0.04em] text-muted-foreground";

export const nodePillPanelClass =
  "flex flex-col gap-3.5 rounded-2xl border border-border bg-muted/30 p-4";

export const nodePillPreviewClass =
  "flex flex-col gap-2.5 rounded-2xl border border-border bg-muted/20 p-4";

export const nodePillLimitTextClass = "text-[0.75rem] text-destructive";

export const nodePillInputRingClass =
  "flex items-center gap-1 rounded-full border border-border bg-card/60 shadow-xs m-2.5";

export const nodePillOptionsListClass = "relative flex flex-col gap-4";

export const nodePillOptionRowClass = "relative flex items-stretch gap-0";

export const nodePillOptionDraggingClass = "opacity-90 z-[2]";

export const nodePillOptionHandleClass =
  "rounded-l-2xl rounded-r-none !p-2";

export const nodePillOptionFieldClass =
  "flex flex-1 flex-col overflow-hidden";

export const nodePillOptionFieldEditClass =
  "rounded-2xl rounded-l-none border border-border focus-within:border-accent transition-colors";

export const nodePillOptionMainClass = "flex items-start min-h-12 pr-0";

export const nodePillOptionGrabClass =
  "flex w-7 shrink-0 self-stretch items-center justify-center border-0 border-l border-border bg-transparent text-muted-foreground cursor-grab select-none p-0 touch-none active:cursor-grabbing active:bg-accent/20";

export const nodePillOptionInlineMetaClass =
  "flex min-h-10 items-center justify-between gap-3 border-t border-border px-3 pl-4 py-2.5";

export const nodePillOptionMetaGroupClass =
  "flex min-w-0 items-center gap-2.5";

export const nodePillOptionMetaLabelClass =
  "text-[0.78rem] text-muted-foreground";

export const nodePillOptionAddClass = "rounded-2xl min-h-11 mx-0.5 mt-1.5";
