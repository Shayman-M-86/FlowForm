import "./styles/index.css";

export type { Theme } from "./components/ui/ThemeProvider";
export { ThemeProvider, useTheme } from "./components/ui/ThemeProvider";

export type { ControlSize, TextareaSize, LayoutGap } from "./lib/sizes";
export {
  controlSizeClasses,
  badgeSizeClasses,
  cardPaddingClasses,
  stackGapClasses,
  textareaBodySizeClasses,
  textareaSizeClasses,
  textareaMinHeights,
  layoutGapClasses,
} from "./lib/sizes";

export type { InputVariant, FocusMode } from "./lib/formFieldStyles";
export {
  formFieldClass,
  formLabelClass,
  formHintClass,
  formErrorClass,
  controlBaseClass,
  getSurfaceClassName,
  getInputControlClassName,
  getTextareaShellClassName,
} from "./lib/formFieldStyles";

export type { StepperSize, StepperVariant } from "./lib/stepperStyles";
export {
  stepperShellClass,
  stepperButtonClass,
  stepperValueClass,
  stepperInputClass,
} from "./lib/stepperStyles";

export { Button } from "./components/ui/Button";
export type { ButtonGroupItem, ButtonGroupTrigger, ButtonGroupGap } from "./components/ui/ButtonGroup";
export { ButtonGroup } from "./components/ui/ButtonGroup";
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
export { PermissionTag } from "./components/ui/PermissionTag";
export type { DropdownMenuAction, DropdownMenuSection, DropdownMenuDirection, DropdownMenuAlign } from "./components/ui/DropdownMenu";
export { DropdownMenu } from "./components/ui/DropdownMenu";
export type { TabSelectorItem } from "./components/ui/TabSelector";
export { TabSelector } from "./components/ui/TabSelector";
export type { TableColumn, TableProps } from "./components/ui/Table";
export { Table } from "./components/ui/Table";
export { Tabs, TabsList, TabsTrigger, TabsContent } from "./components/ui/tabs";
export type { ToastVariant } from "./components/ui/Toast";
export { Toast } from "./components/ui/Toast";
