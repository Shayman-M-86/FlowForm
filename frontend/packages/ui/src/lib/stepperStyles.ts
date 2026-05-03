import { cn } from "./utils";

export type StepperSize = "xs" | "sm";
export type StepperVariant = "primary" | "secondary" | "ghost";

const stepperShellVariantClasses: Record<StepperVariant, string> = {
  primary: "ui-stepper-shell-primary",
  secondary: "ui-stepper-shell-secondary",
  ghost: "ui-stepper-shell-ghost",
};

function stepperShellRadiusClass(size: StepperSize, pill: boolean) {
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
}) {
  return cn(
    "ui-stepper-shell",
    stepperShellVariantClasses[variant],
    stepperShellRadiusClass(size, pill),
  );
}

function stepperButtonWidthClass(size: StepperSize) {
  return size === "xs" ? "min-w-[22px]" : "min-w-[28px]";
}

function stepperButtonRadiusClass(pill: boolean) {
  return pill ? "rounded-full" : "rounded-md";
}

function stepperButtonToneClass(variant: StepperVariant) {
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
}) {
  return cn(
    "ui-stepper-button",
    stepperButtonWidthClass(size),
    stepperButtonRadiusClass(pill),
    stepperButtonToneClass(variant),
  );
}

export function stepperValueClass(size: StepperSize) {
  return cn(
    "ui-stepper-value",
    size === "xs" ? "min-w-[22px] text-[0.82rem]" : "min-w-[28px]",
  );
}

export function stepperInputClass(size: StepperSize) {
  return cn(
    "ui-stepper-input",
    size === "xs" && "text-[0.82rem]",
  );
}
