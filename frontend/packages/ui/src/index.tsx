import "./styles/index.css";

export type { Theme } from "./components/ui/ThemeProvider";
export { ThemeProvider, useTheme } from "./components/ui/ThemeProvider";

export type { ControlSize, TextareaSize, LayoutGap } from "./lib/sizes.ts";
export {
  controlSizeClasses,
  badgeSizeClasses,
  cardPaddingClasses,
  stackGapClasses,
  textareaBodySizeClasses,
  textareaSizeClasses,
  textareaMinHeights,
  layoutGapClasses,
} from "./lib/sizes.ts";

export type { InputVariant, FocusMode } from "./lib/formFieldStyles.ts";
export {
  formFieldClass,
  formLabelClass,
  formHintClass,
  formErrorClass,
  controlBaseClass,
  getSurfaceClassName,
  getInputControlClassName,
  getTextareaShellClassName,
} from "./lib/formFieldStyles.ts";

export type { StepperSize, StepperVariant } from "./lib/stepperStyles.ts";
export {
  stepperShellClass,
  stepperButtonClass,
  stepperValueClass,
  stepperInputClass,
} from "./lib/stepperStyles.ts";

export { Button } from "./components/ui/Button";
export { Card, CardRow, CardStack } from "./components/ui/Card";
export { ExpandableSelector } from "./components/ui/ExpandableSelector";
export { ExpandableTextArea } from "./components/ui/ExpandableTextArea";
export { Input } from "./components/ui/Input";
export { LargeInput } from "./components/ui/LargeInput";
export { Modal } from "./components/ui/Modal";
export { NumberStepper } from "./components/ui/NumberStepper";
export { NumberStepperGroup } from "./components/ui/NumberStepperGroup";
export { Select } from "./components/ui/Select";
export type { SelectChangeEvent } from "./components/ui/Select";
export { Spinner } from "./components/ui/Spinner";
export { ThemeToggle } from "./components/ui/ThemeToggle";
export { Toggle } from "./components/ui/Toggle";
export { Tooltip } from "./components/ui/Tooltip";
export { Badge } from "./components/ui/Badge";
export type { DropdownMenuAction, DropdownMenuSection } from "./components/ui/DropdownMenu";
export { DropdownMenu } from "./components/ui/DropdownMenu";
