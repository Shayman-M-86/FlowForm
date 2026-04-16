import { useState } from "react";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Input } from "../components/ui/Input";
import { LargeInput } from "../components/ui/LargeInput";
import { Select } from "../components/ui/Select";
import { Tooltip } from "../components/ui/Tooltip";
import { Toggle } from "../components/ui/Toggle";
import { Spinner } from "../components/ui/Spinner";
import { Modal } from "../components/ui/Modal";
import { NumberStepper } from "../components/ui/NumberStepper";
import { NumberStepperGroup } from "../components/ui/NumberStepperGroup";
import "./UITestPage.css";

const buttonVariants = ["primary", "secondary", "dark", "danger", "ghost", "quiet"] as const;
const buttonSizes = ["md", "sm", "xs"] as const;
const buttonVariantLabels: Record<(typeof buttonVariants)[number], string> = {
  primary: "Primary",
  secondary: "Secondary",
  dark: "Dark",
  danger: "Danger",
  ghost: "Ghost",
  quiet: "Quiet",
};
const buttonSizeLabels: Record<(typeof buttonSizes)[number], string> = {
  md: "MD",
  sm: "SM",
  xs: "XS",
};

export function UITestPage() {
  const [toggleStates, setToggleStates] = useState({
    toggle1: false,
    toggle2: true,
  });
  const [largeInputValues, setLargeInputValues] = useState({
    controlled: "",
    counted: "Initial summary text for the counted large input.",
    autoGrow:
      "Start typing here to test auto-grow.\n\nThis example begins with multiple lines so the resize behavior is visible immediately.",
  });
  const [selectValue, setSelectValue] = useState("option1");
  const [modalOpen, setModalOpen] = useState(false);
  const [stepperValues, setStepperValues] = useState({
    sm: 5,
    smSecondary: 5,
    smPill: 5,
    smSecondaryPill: 5,
    xs: 5,
    xsPill: 5,
    stepped: 10,
  });
  const [rangeGroups, setRangeGroups] = useState({
    sm: { min: 1, max: 2 },
    smSecondary: { min: 1, max: 2 },
    smPill: { min: 2, max: 6 },
    smSecondaryPill: { min: 2, max: 6 },
    smInput: { min: 2, max: 8 },
    xs: { min: 1, max: 2 },
    xsPill: { min: 3, max: 7 },
    stepped: { min: 10, max: 20 },
  });

  const handleToggle = (key: string, checked: boolean) => {
    setToggleStates((prev) => ({ ...prev, [key]: checked }));
  };

  const updateLargeInputValue = (
    key: keyof typeof largeInputValues,
    value: string,
  ) => {
    setLargeInputValues((current) => ({ ...current, [key]: value }));
  };

  const updateStepperValue = (key: keyof typeof stepperValues, value: number) => {
    setStepperValues((current) => ({ ...current, [key]: value }));
  };

  const updateRangeGroup = (
    groupKey: keyof typeof rangeGroups,
    itemKey: "min" | "max",
    value: number,
  ) => {
    setRangeGroups((current) => ({
      ...current,
      [groupKey]: {
        ...current[groupKey],
        [itemKey]: value,
      },
    }));
  };

  return (
    <div className="ui-test-page">
      <div className="ui-test-container">
        <h1>UI Component Test Suite</h1>

        {/* Buttons Section */}
        <section className="ui-test-section">
          <h2>Buttons</h2>
          <div className="ui-test-grid">
            {buttonVariants.map((variant) => (
              <div key={`${variant}-standard`} className="ui-test-card">
                <h3>{buttonVariantLabels[variant]} / Standard</h3>
                <div className="ui-test-button-row">
                  {buttonSizes.map((size) => (
                    <Button key={`${variant}-${size}`} variant={variant} size={size}>
                      {buttonSizeLabels[size]}
                    </Button>
                  ))}
                </div>
              </div>
            ))}
            {buttonVariants.map((variant) => (
              <div key={`${variant}-pill`} className="ui-test-card">
                <h3>{buttonVariantLabels[variant]} / Pill</h3>
                <div className="ui-test-button-row">
                  {buttonSizes.map((size) => (
                    <Button key={`${variant}-${size}-pill`} variant={variant} size={size} pill>
                      {buttonSizeLabels[size]}
                    </Button>
                  ))}
                </div>
              </div>
            ))}
            {buttonVariants.map((variant) => (
              <div key={`${variant}-disabled`} className="ui-test-card">
                <h3>{buttonVariantLabels[variant]} / Disabled</h3>
                <div className="ui-test-button-row">
                  {buttonSizes.map((size) => (
                    <Button key={`${variant}-${size}-disabled`} variant={variant} size={size} disabled>
                      {buttonSizeLabels[size]}
                    </Button>
                  ))}
                </div>
              </div>
            ))}
            {buttonVariants.map((variant) => (
              <div key={`${variant}-dotted`} className="ui-test-card">
                <h3>{buttonVariantLabels[variant]} / Dotted Border</h3>
                <div className="ui-test-button-row">
                  {buttonSizes.map((size) => (
                    <Button
                      key={`${variant}-${size}-dotted`}
                      variant={variant}
                      size={size}
                      borderStyle="dotted"
                    >
                      {buttonSizeLabels[size]}
                    </Button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Tooltip Section */}
        <section className="ui-test-section">
          <h2>Tooltip</h2>
          <div className="ui-test-grid">
            <div className="ui-test-card">
              <h3>Ghost Button Sizes</h3>
              <div className="ui-test-stack">
                <Tooltip title="Delete" size="sm">
                  <Button variant="ghost">Small</Button>
                </Tooltip>

                <Tooltip title="Delete" size="md">
                  <Button variant="ghost">Medium</Button>
                </Tooltip>

                <Tooltip title="Delete" size="lg">
                  <Button variant="ghost">Large</Button>
                </Tooltip>
              </div>
            </div>
          </div>
        </section>

        {/* Large Input Section */}
        <section className="ui-test-section">
          <h2>Large Input</h2>
          <div className="ui-test-grid">
            <div className="ui-test-card">
              <h3>Size SM / Placeholder</h3>
              <LargeInput
                label="Quick Note"
                size="sm"
                placeholder="Write a short note..."
                hint="Tests size, label, placeholder, and name"
                name="quickNote"
              />
            </div>
            <div className="ui-test-card">
              <h3>Size MD / Rows</h3>
              <LargeInput
                label="Description"
                size="md"
                rows={5}
                defaultValue="Medium large-input variant with a little more room for longer messages."
                placeholder="Add a medium-length description..."
                hint="Tests default value and rows"
              />
            </div>
            <div className="ui-test-card">
              <h3>Size LG / Placeholder</h3>
              <LargeInput
                label="Detailed Summary"
                size="lg"
                placeholder="Write a detailed summary..."
                hint="Expanded large-input size"
                required
                autoComplete="off"
              />
            </div>
            <div className="ui-test-card">
              <h3>Controlled Value</h3>
              <LargeInput
                label="Controlled Notes"
                size="md"
                value={largeInputValues.controlled}
                onChange={(event) =>
                  updateLargeInputValue("controlled", event.target.value)
                }
                placeholder="Type to test value and onChange..."
                hint="Tests controlled textarea behavior"
              />
            </div>
            <div className="ui-test-card">
              <h3>Character Count</h3>
              <LargeInput
                label="Summary"
                size="md"
                value={largeInputValues.counted}
                onChange={(event) =>
                  updateLargeInputValue("counted", event.target.value)
                }
                placeholder="Write a concise summary..."
                hint="Tests maxText and showCount"
                maxText={180}
                showCount
              />
            </div>
            <div className="ui-test-card">
              <h3>Auto Grow</h3>
              <LargeInput
                label="Auto-Growing Notes"
                size="sm"
                value={largeInputValues.autoGrow}
                onChange={(event) =>
                  updateLargeInputValue("autoGrow", event.target.value)
                }
                placeholder="Type multiple lines to grow the field..."
                hint="Tests autoGrow and maxAutoGrowHeight"
                autoGrow
                maxAutoGrowHeight={220}
              />
            </div>
            <div className="ui-test-card">
              <h3>Error State</h3>
              <LargeInput
                label="Feedback"
                size="md"
                placeholder="Explain what went wrong..."
                error="Feedback is required before continuing."
              />
            </div>
            <div className="ui-test-card">
              <h3>Disabled</h3>
              <LargeInput
                label="Archived Notes"
                size="sm"
                defaultValue="This field is disabled."
                placeholder="Disabled input"
                disabled
                hint="Disabled textarea state"
              />
            </div>
            <div className="ui-test-card">
              <h3>Read Only</h3>
              <LargeInput
                label="Reference Copy"
                size="sm"
                defaultValue="This content is read-only but still selectable."
                placeholder="Read-only input"
                readOnly
                hint="Tests readOnly behavior"
              />
            </div>
          </div>
        </section>

        {/* Number Up/Down Section */}
        <section className="ui-test-section">
          <h2>Number Up/Down</h2>
          <div className="ui-test-grid">
            <div className="ui-test-card">
              <h3>Size SM Primary</h3>
              <NumberStepper
                value={stepperValues.sm}
                onChange={(value) => updateStepperValue("sm", value)}
                min={1}
                max={10}
                step={1}
                size="sm"
                variant="primary"
              />
            </div>
            <div className="ui-test-card">
              <h3>Size SM Primary Pill</h3>
              <NumberStepper
                value={stepperValues.smPill}
                onChange={(value) => updateStepperValue("smPill", value)}
                min={1}
                max={10}
                step={1}
                size="sm"
                variant="primary"
                pill
              />
            </div>
            <div className="ui-test-card">
              <h3>Size SM Secondary</h3>
              <NumberStepper
                value={stepperValues.smSecondary}
                onChange={(value) => updateStepperValue("smSecondary", value)}
                min={1}
                max={10}
                step={1}
                size="sm"
                variant="secondary"
              />
            </div>
            <div className="ui-test-card">
              <h3>Size SM Secondary Pill</h3>
              <NumberStepper
                value={stepperValues.smSecondaryPill}
                onChange={(value) => updateStepperValue("smSecondaryPill", value)}
                min={1}
                max={10}
                step={1}
                size="sm"
                pill
                variant="secondary"
              />
            </div>
            <div className="ui-test-card">
              <h3>Size XS Ghost</h3>
              <NumberStepper
                value={stepperValues.xs}
                onChange={(value) => updateStepperValue("xs", value)}
                min={1}
                max={10}
                step={1}
                size="xs"
                variant="ghost"
              />
            </div>
            <div className="ui-test-card">
              <h3>Size XS Ghost Pill</h3>
              <NumberStepper
                value={stepperValues.xsPill}
                onChange={(value) => updateStepperValue("xsPill", value)}
                min={1}
                max={10}
                step={1}
                size="xs"
                variant="ghost"
                pill
              />
            </div>
            <div className="ui-test-card">
              <h3>Range 0-100, Step 5</h3>
              <NumberStepper
                value={stepperValues.stepped}
                onChange={(value) => updateStepperValue("stepped", value)}
                min={0}
                max={100}
                step={5}
              />
            </div>
            <div className="ui-test-card">
              <h3>Disabled</h3>
              <NumberStepper
                value={5}
                onChange={() => { }}
                disabled
              />
            </div>
          </div>
        </section>

        {/* Number Stepper Group Section */}
        <section className="ui-test-section">
          <h2>Number Stepper Group</h2>
          <div className="ui-test-grid">
            <div className="ui-test-card">
              <h3>Size SM Primary</h3>
              <NumberStepperGroup
                size="sm"
                variant="primary"
                items={[
                  { key: "min", label: "Min", value: rangeGroups.sm.min, min: 0, max: 10 },
                  { key: "max", label: "Max", value: rangeGroups.sm.max, min: 0, max: 10 },
                ]}
                onChange={(key, value) => updateRangeGroup("sm", key as "min" | "max", value)}
              />
            </div>
            <div className="ui-test-card">
              <h3>Size SM Primary Pill</h3>
              <NumberStepperGroup
                size="sm"
                variant="primary"
                pill
                items={[
                  { key: "min", label: "Min", value: rangeGroups.smPill.min, min: 0, max: 10 },
                  { key: "max", label: "Max", value: rangeGroups.smPill.max, min: 0, max: 10 },
                ]}
                onChange={(key, value) => updateRangeGroup("smPill", key as "min" | "max", value)}
              />
            </div>
            <div className="ui-test-card">
              <h3>Size SM Secondary</h3>
              <NumberStepperGroup
                size="sm"
                variant="secondary"
                items={[
                  { key: "min", label: "Min", value: rangeGroups.smSecondary.min, min: 0, max: 10 },
                  { key: "max", label: "Max", value: rangeGroups.smSecondary.max, min: 0, max: 10 },
                ]}
                onChange={(key, value) => updateRangeGroup("smSecondary", key as "min" | "max", value)}
              />
            </div>
            <div className="ui-test-card">
              <h3>Size SM Secondary Pill</h3>
              <NumberStepperGroup
                size="sm"
                pill
                variant="secondary"
                items={[
                  { key: "min", label: "Min", value: rangeGroups.smSecondaryPill.min, min: 0, max: 10 },
                  { key: "max", label: "Max", value: rangeGroups.smSecondaryPill.max, min: 0, max: 10 },
                ]}
                onChange={(key, value) => updateRangeGroup("smSecondaryPill", key as "min" | "max", value)}
              />
            </div>
            <div className="ui-test-card">
              <h3>Size SM Secondary Input</h3>
              <NumberStepperGroup
                size="sm"
                variant="secondary"
                allowInput
                items={[
                  { key: "min", label: "Min", value: rangeGroups.smInput.min, min: 0, max: 10 },
                  { key: "max", label: "Max", value: rangeGroups.smInput.max, min: 0, max: 10 },
                ]}
                onChange={(key, value) => updateRangeGroup("smInput", key as "min" | "max", value)}
              />
            </div>
            <div className="ui-test-card">
              <h3>Size XS Ghost</h3>
              <NumberStepperGroup
                size="xs"
                variant="ghost"
                items={[
                  { key: "min", label: "Min", value: rangeGroups.xs.min, min: 0, max: 10 },
                  { key: "max", label: "Max", value: rangeGroups.xs.max, min: 0, max: 10 },
                ]}
                onChange={(key, value) => updateRangeGroup("xs", key as "min" | "max", value)}
              />
            </div>
            <div className="ui-test-card">
              <h3>Size XS Ghost Pill</h3>
              <NumberStepperGroup
                size="xs"
                variant="ghost"
                pill
                items={[
                  { key: "min", label: "Min", value: rangeGroups.xsPill.min, min: 0, max: 10 },
                  { key: "max", label: "Max", value: rangeGroups.xsPill.max, min: 0, max: 10 },
                ]}
                onChange={(key, value) => updateRangeGroup("xsPill", key as "min" | "max", value)}
              />
            </div>
            <div className="ui-test-card">
              <h3>Step 5 / Wide Range</h3>
              <NumberStepperGroup
                size="sm"
                items={[
                  { key: "min", label: "Min", value: rangeGroups.stepped.min, min: 0, max: 50, step: 5 },
                  { key: "max", label: "Max", value: rangeGroups.stepped.max, min: 0, max: 50, step: 5 },
                ]}
                onChange={(key, value) => updateRangeGroup("stepped", key as "min" | "max", value)}
              />
            </div>
            <div className="ui-test-card">
              <h3>Disabled</h3>
              <NumberStepperGroup
                size="sm"
                items={[
                  { key: "min", label: "Min", value: 2, min: 0, max: 10, disabled: true },
                  { key: "max", label: "Max", value: 6, min: 0, max: 10, disabled: true },
                ]}
                onChange={() => { }}
              />
            </div>
          </div>
        </section>

        {/* Badges Section */}
        <section className="ui-test-section">
          <h2>Badges</h2>
          <div className="ui-test-grid">
            <div className="ui-test-card">
              <h3>Default</h3>
              <Badge>Default Badge</Badge>
            </div>
            <div className="ui-test-card">
              <h3>Success</h3>
              <Badge variant="success">Success Badge</Badge>
            </div>
            <div className="ui-test-card">
              <h3>Danger</h3>
              <Badge variant="danger">Danger Badge</Badge>
            </div>
            <div className="ui-test-card">
              <h3>Warning</h3>
              <Badge variant="warning">Warning Badge</Badge>
            </div>
            <div className="ui-test-card">
              <h3>Accent</h3>
              <Badge variant="accent">Accent Badge</Badge>
            </div>
            <div className="ui-test-card">
              <h3>Muted</h3>
              <Badge variant="muted">Muted Badge</Badge>
            </div>
            <div className="ui-test-card">
              <h3>Sizes</h3>
              <div className="ui-test-stack">
                <Badge size="sm">Small</Badge>
                <Badge size="md">Medium</Badge>
                <Badge size="lg">Large</Badge>
                <Badge size="xl">Extra Large</Badge>
              </div>
            </div>
          </div>
        </section>

        {/* Inputs Section */}
        <section className="ui-test-section">
          <h2>Inputs</h2>
          <div className="ui-test-grid">
            <div className="ui-test-card">
              <h3>Default</h3>
              <Input
                label="Name"
                placeholder="Default"
              />
            </div>
            <div className="ui-test-card">
              <h3>Small</h3>
              <Input
                label="Compact"
                size="sm"
                placeholder="Smaller input"
              />
            </div>
            <div className="ui-test-card">
              <h3>Ghost</h3>
              <Input
                label="Ghost"
                variant="ghost"
                placeholder="Ghost input"
              />
            </div>
            <div className="ui-test-card">
              <h3>Quiet</h3>
              <Input
                label="Quiet"
                variant="quiet"
                placeholder="Quiet input"
              />
            </div>
            <div className="ui-test-card">
              <h3>Pill</h3>
              <Input
                label="Pill"
                variant="secondary"
                pill
                placeholder="Pill input"
              />
            </div>
            <div className="ui-test-card">
              <h3>Disabled</h3>
              <Input
                label="Disabled"
                variant="quiet"
                disabled
                value="Disabled value"
              />
            </div>
          </div>
        </section>

        {/* Select Section */}
        <section className="ui-test-section">
          <h2>Select Dropdown</h2>
          <div className="ui-test-grid">
            <div className="ui-test-card">
              <Select
                label="Choose an option"
                options={[
                  { value: "option1", label: "Option 1" },
                  { value: "option2", label: "Option 2" },
                  { value: "option3", label: "Option 3" },
                ]}
                value={selectValue}
                onChange={(e) => setSelectValue(e.target.value)}
              />
            </div>
            <div className="ui-test-card">
              <Select
                label="With Hint"
                options={[
                  { value: "yes", label: "Yes" },
                  { value: "no", label: "No" },
                  { value: "maybe", label: "Maybe" },
                ]}
                hint="Select one of the options above"
              />
            </div>
          </div>
        </section>

        {/* Toggles Section */}
        <section className="ui-test-section">
          <h2>Toggles</h2>
          <div className="ui-test-grid">
            <div className="ui-test-card">
              <Toggle
                label="Enable notifications"
                checked={toggleStates.toggle1}
                onChange={(checked) => handleToggle("toggle1", checked)}
              />
            </div>
            <div className="ui-test-card">
              <Toggle
                label="Dark mode (enabled)"
                checked={toggleStates.toggle2}
                onChange={(checked) => handleToggle("toggle2", checked)}
              />
            </div>
            <div className="ui-test-card">
              <Toggle
                label="Disabled toggle"
                checked={false}
                onChange={() => { }}
                disabled
              />
            </div>
            <div className="ui-test-card">
              <Toggle
                label="With hint text"
                checked={toggleStates.toggle1}
                onChange={(checked) => handleToggle("toggle1", checked)}
                hint="This toggle has a helpful hint below"
              />
            </div>
          </div>
        </section>

        {/* Spinner Section */}
        <section className="ui-test-section">
          <h2>Spinners</h2>
          <div className="ui-test-grid">
            <div className="ui-test-card">
              <h3>Small (16px)</h3>
              <Spinner size={16} />
            </div>
            <div className="ui-test-card">
              <h3>Medium (24px)</h3>
              <Spinner size={24} />
            </div>
            <div className="ui-test-card">
              <h3>Large (32px)</h3>
              <Spinner size={32} />
            </div>
            <div className="ui-test-card">
              <h3>Extra Large (48px)</h3>
              <Spinner size={48} />
            </div>
          </div>
        </section>

        {/* Modal Section */}
        <section className="ui-test-section">
          <h2>Modal</h2>
          <div className="ui-test-grid">
            <div className="ui-test-card">
              <Button variant="primary" onClick={() => setModalOpen(true)}>
                Open Modal
              </Button>
            </div>
          </div>
        </section>

        <Modal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          title="Test Modal"
          footer={
            <div className="modal-footer-actions">
              <Button variant="secondary" onClick={() => setModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={() => setModalOpen(false)}>
                Confirm
              </Button>
            </div>
          }
        >
          <p>This is a test modal dialog. You can interact with all the UI components inside it.</p>
          <Input label="Modal Input" placeholder="Type something..." />
          <Select
            label="Modal Select"
            options={[
              { value: "opt1", label: "Option 1" },
              { value: "opt2", label: "Option 2" },
            ]}
          />
        </Modal>
      </div>
    </div>
  );
}
