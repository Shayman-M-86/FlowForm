export type StepperSize = "xs" | "sm";
export type StepperVariant = "primary" | "secondary" | "ghost";

const shellBase =
  "inline-flex w-fit items-center self-start border transition-colors";

const shellVariant: Record<StepperVariant, string> = {
  primary: "bg-primary/10 border-primary/60",
  secondary: "bg-input border-secondary/10",
  ghost: "bg-transparent border-transparent",
};

function shellRadius(size: StepperSize, pill: boolean): string {
  if (pill) return "rounded-full";
  return size === "xs" ? "rounded-md" : "rounded-sm";
}

export function stepperShellClass({
  size,
  variant,
  pill,
}: {
  size: StepperSize;
  variant: StepperVariant;
  pill: boolean;
}): string {
  return [shellBase, shellVariant[variant], shellRadius(size, pill)].join(" ");
}

const buttonBase = "border-transparent bg-transparent p-0 shadow-none hover:bg-muted";

function buttonMinWidth(size: StepperSize): string {
  return size === "xs" ? "min-w-[22px]" : "min-w-[28px]";
}

function buttonRadius(pill: boolean): string {
  return pill ? "rounded-full" : "rounded-md";
}

function buttonColor(variant: StepperVariant): string {
  return variant === "ghost"
    ? "text-muted-foreground hover:text-foreground"
    : "text-foreground";
}

export function stepperButtonClass({
  size,
  variant,
  pill,
}: {
  size: StepperSize;
  variant: StepperVariant;
  pill: boolean;
}): string {
  return [
    buttonBase,
    buttonMinWidth(size),
    buttonRadius(pill),
    buttonColor(variant),
  ].join(" ");
}

const valueBase =
  "select-none text-center font-medium text-foreground tabular-nums";

export function stepperValueClass(size: StepperSize): string {
  return [
    valueBase,
    size === "xs" ? "min-w-[22px] text-[0.82rem]" : "min-w-[28px]",
  ].join(" ");
}

export function stepperInputClass(size: StepperSize): string {
  return [
    "w-[42px] text-center tabular-nums",
    size === "xs" ? "text-[0.82rem]" : "",
  ]
    .filter(Boolean)
    .join(" ");
}
