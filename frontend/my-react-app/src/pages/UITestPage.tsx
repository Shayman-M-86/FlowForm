import { useState } from "react";
import {
  Button,
  Card,
  CardRow,
  CardStack,
  Input,
  LargeInput,
  Select,
  Tooltip,
  Toggle,
  Spinner,
  Modal,
  NumberStepper,
  NumberStepperGroup,
  ThemeToggle,
, Badge
} from "../index.optimized";

const buttonVariants = ["primary", "secondary", "danger", "ghost"] as const;
const buttonSizes = ["md", "sm", "xs"] as const;

const buttonVariantLabels: Record<(typeof buttonVariants)[number], string> = {
  primary: "Primary",
  secondary: "Secondary",
  danger: "Danger",
  ghost: "Ghost",
};

const buttonSizeLabels: Record<(typeof buttonSizes)[number], string> = {
  md: "MD",
  sm: "SM",
  xs: "XS",
};

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mb-12 md:mb-16">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

function TestGrid({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-1 gap-5 md:grid-cols-[repeat(auto-fit,minmax(280px,1fr))]">
      {children}
    </div>
  );
}

function TestCard({
  title,
  children,
}: {
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <Card size="md">
      <CardStack gap="sm">
        {title ? <h3 className="section-label">{title}</h3> : null}
        {children}
      </CardStack>
    </Card>
  );
}

function InlineStack({ children }: { children: React.ReactNode }) {
  return <CardRow gap="xs">{children}</CardRow>;
}

function WideStack({ children }: { children: React.ReactNode }) {
  return <CardRow gap="sm">{children}</CardRow>;
}

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
    <div className="min-h-screen w-full bg-background px-4 py-5 text-foreground md:px-5 md:py-10">
      <div className="mx-auto max-w-[1400px]">
        <div className="mb-8 flex items-center justify-between gap-4 border-b-2 border-border pb-5 md:mb-10">
          <h1 className="m-0">UI Component Test Suite</h1>
          <ThemeToggle />
        </div>

        <Section title="Buttons">
          <TestGrid>
            {buttonVariants.map((variant) => (
              <TestCard
                key={`${variant}-standard`}
                title={`${buttonVariantLabels[variant]} / Standard`}
              >
                <InlineStack>
                  {buttonSizes.map((size) => (
                    <Button key={`${variant}-${size}`} variant={variant} size={size}>
                      {buttonSizeLabels[size]}
                    </Button>
                  ))}
                </InlineStack>
              </TestCard>
            ))}

            {buttonVariants.map((variant) => (
              <TestCard
                key={`${variant}-pill`}
                title={`${buttonVariantLabels[variant]} / Pill`}
              >
                <InlineStack>
                  {buttonSizes.map((size) => (
                    <Button key={`${variant}-${size}-pill`} variant={variant} size={size} pill>
                      {buttonSizeLabels[size]}
                    </Button>
                  ))}
                </InlineStack>
              </TestCard>
            ))}

            {buttonVariants.map((variant) => (
              <TestCard
                key={`${variant}-disabled`}
                title={`${buttonVariantLabels[variant]} / Disabled`}
              >
                <InlineStack>
                  {buttonSizes.map((size) => (
                    <Button
                      key={`${variant}-${size}-disabled`}
                      variant={variant}
                      size={size}
                      disabled
                    >
                      {buttonSizeLabels[size]}
                    </Button>
                  ))}
                </InlineStack>
              </TestCard>
            ))}

            {buttonVariants.map((variant) => (
              <TestCard
                key={`${variant}-dotted`}
                title={`${buttonVariantLabels[variant]} / Dotted Border`}
              >
                <InlineStack>
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
                </InlineStack>
              </TestCard>
            ))}
          </TestGrid>
        </Section>

        <Section title="Tooltip">
          <TestGrid>
            <TestCard title="Ghost Button Sizes">
              <WideStack>
                <Tooltip title="Delete" size="sm">
                  <Button variant="ghost">Small</Button>
                </Tooltip>

                <Tooltip title="Delete" size="md">
                  <Button variant="ghost">Medium</Button>
                </Tooltip>

                <Tooltip title="Delete" size="lg">
                  <Button variant="ghost">Large</Button>
                </Tooltip>
              </WideStack>
            </TestCard>
          </TestGrid>
        </Section>

        <Section title="Large Input">
          <TestGrid>
            <TestCard title="Size SM / Placeholder">
              <LargeInput
                label="Quick Note"
                size="sm"
                placeholder="Write a short note..."
                hint="Tests size, label, placeholder, and name"
                name="quickNote"
              />
            </TestCard>

            <TestCard title="Size MD / Rows">
              <LargeInput
                label="Description"
                size="md"
                rows={5}
                defaultValue="Medium large-input variant with a little more room for longer messages."
                placeholder="Add a medium-length description..."
                hint="Tests default value and rows"
              />
            </TestCard>

            <TestCard title="Size LG / Placeholder">
              <LargeInput
                label="Detailed Summary"
                size="lg"
                placeholder="Write a detailed summary..."
                hint="Expanded large-input size"
                required
                autoComplete="off"
              />
            </TestCard>

            <TestCard title="Controlled Value">
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
            </TestCard>

            <TestCard title="Character Count">
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
            </TestCard>

            <TestCard title="Auto Grow">
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
            </TestCard>

            <TestCard title="Error State">
              <LargeInput
                label="Feedback"
                size="md"
                placeholder="Explain what went wrong..."
                error="Feedback is required before continuing."
              />
            </TestCard>

            <TestCard title="Disabled">
              <LargeInput
                label="Archived Notes"
                size="sm"
                defaultValue="This field is disabled."
                placeholder="Disabled input"
                disabled
                hint="Disabled textarea state"
              />
            </TestCard>

            <TestCard title="Read Only">
              <LargeInput
                label="Reference Copy"
                size="sm"
                defaultValue="This content is read-only but still selectable."
                placeholder="Read-only input"
                readOnly
                hint="Tests readOnly behavior"
              />
            </TestCard>
          </TestGrid>
        </Section>

        <Section title="Number Up/Down">
          <TestGrid>
            <TestCard title="Size SM Primary">
              <NumberStepper
                value={stepperValues.sm}
                onChange={(value) => updateStepperValue("sm", value)}
                min={1}
                max={10}
                step={1}
                size="sm"
                variant="primary"
              />
            </TestCard>

            <TestCard title="Size SM Primary Pill">
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
            </TestCard>

            <TestCard title="Size SM Secondary">
              <NumberStepper
                value={stepperValues.smSecondary}
                onChange={(value) => updateStepperValue("smSecondary", value)}
                min={1}
                max={10}
                step={1}
                size="sm"
                variant="secondary"
              />
            </TestCard>

            <TestCard title="Size SM Secondary Pill">
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
            </TestCard>

            <TestCard title="Size XS Ghost">
              <NumberStepper
                value={stepperValues.xs}
                onChange={(value) => updateStepperValue("xs", value)}
                min={1}
                max={10}
                step={1}
                size="xs"
                variant="ghost"
              />
            </TestCard>

            <TestCard title="Size XS Ghost Pill">
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
            </TestCard>

            <TestCard title="Range 0-100, Step 5">
              <NumberStepper
                value={stepperValues.stepped}
                onChange={(value) => updateStepperValue("stepped", value)}
                min={0}
                max={100}
                step={5}
              />
            </TestCard>

            <TestCard title="Disabled">
              <NumberStepper value={5} onChange={() => {}} disabled />
            </TestCard>
          </TestGrid>
        </Section>

        <Section title="Number Stepper Group">
          <TestGrid>
            <TestCard title="Size SM Primary">
              <NumberStepperGroup
                size="sm"
                variant="primary"
                items={[
                  { key: "min", label: "Min", value: rangeGroups.sm.min, min: 0, max: 10 },
                  { key: "max", label: "Max", value: rangeGroups.sm.max, min: 0, max: 10 },
                ]}
                onChange={(key, value) => updateRangeGroup("sm", key as "min" | "max", value)}
              />
            </TestCard>

            <TestCard title="Size SM Primary Pill">
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
            </TestCard>

            <TestCard title="Size SM Secondary">
              <NumberStepperGroup
                size="sm"
                variant="secondary"
                items={[
                  { key: "min", label: "Min", value: rangeGroups.smSecondary.min, min: 0, max: 10 },
                  { key: "max", label: "Max", value: rangeGroups.smSecondary.max, min: 0, max: 10 },
                ]}
                onChange={(key, value) =>
                  updateRangeGroup("smSecondary", key as "min" | "max", value)
                }
              />
            </TestCard>

            <TestCard title="Size SM Secondary Pill">
              <NumberStepperGroup
                size="sm"
                pill
                variant="secondary"
                items={[
                  { key: "min", label: "Min", value: rangeGroups.smSecondaryPill.min, min: 0, max: 10 },
                  { key: "max", label: "Max", value: rangeGroups.smSecondaryPill.max, min: 0, max: 10 },
                ]}
                onChange={(key, value) =>
                  updateRangeGroup("smSecondaryPill", key as "min" | "max", value)
                }
              />
            </TestCard>

            <TestCard title="Size SM Secondary Input">
              <NumberStepperGroup
                size="sm"
                variant="secondary"
                allowInput
                items={[
                  { key: "min", label: "Min", value: rangeGroups.smInput.min, min: 0, max: 10 },
                  { key: "max", label: "Max", value: rangeGroups.smInput.max, min: 0, max: 10 },
                ]}
                onChange={(key, value) =>
                  updateRangeGroup("smInput", key as "min" | "max", value)
                }
              />
            </TestCard>

            <TestCard title="Size XS Ghost">
              <NumberStepperGroup
                size="xs"
                variant="ghost"
                items={[
                  { key: "min", label: "Min", value: rangeGroups.xs.min, min: 0, max: 10 },
                  { key: "max", label: "Max", value: rangeGroups.xs.max, min: 0, max: 10 },
                ]}
                onChange={(key, value) => updateRangeGroup("xs", key as "min" | "max", value)}
              />
            </TestCard>

            <TestCard title="Size XS Ghost Pill">
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
            </TestCard>

            <TestCard title="Step 5 / Wide Range">
              <NumberStepperGroup
                size="sm"
                items={[
                  { key: "min", label: "Min", value: rangeGroups.stepped.min, min: 0, max: 50, step: 5 },
                  { key: "max", label: "Max", value: rangeGroups.stepped.max, min: 0, max: 50, step: 5 },
                ]}
                onChange={(key, value) =>
                  updateRangeGroup("stepped", key as "min" | "max", value)
                }
              />
            </TestCard>

            <TestCard title="Disabled">
              <NumberStepperGroup
                size="sm"
                items={[
                  { key: "min", label: "Min", value: 2, min: 0, max: 10, disabled: true },
                  { key: "max", label: "Max", value: 6, min: 0, max: 10, disabled: true },
                ]}
                onChange={() => {}}
              />
            </TestCard>
          </TestGrid>
        </Section>

        <Section title="Badges">
          <TestGrid>
            <TestCard title="Default">
              <Badge>Default Badge</Badge>
            </TestCard>
            <TestCard title="Success">
              <Badge variant="success">Success Badge</Badge>
            </TestCard>
            <TestCard title="Danger">
              <Badge variant="danger">Danger Badge</Badge>
            </TestCard>
            <TestCard title="Warning">
              <Badge variant="warning">Warning Badge</Badge>
            </TestCard>
            <TestCard title="Accent">
              <Badge variant="accent">Accent Badge</Badge>
            </TestCard>
            <TestCard title="Muted">
              <Badge variant="muted">Muted Badge</Badge>
            </TestCard>
            <TestCard title="Sizes">
              <WideStack>
                <Badge size="sm">Small</Badge>
                <Badge size="md">Medium</Badge>
                <Badge size="lg">Large</Badge>
                <Badge size="xl">Extra Large</Badge>
              </WideStack>
            </TestCard>
          </TestGrid>
        </Section>

        <Section title="Inputs">
          <TestGrid>
            <TestCard title="Default">
              <Input label="Name" placeholder="Default" />
            </TestCard>
            <TestCard title="Small">
              <Input label="Compact" size="sm" placeholder="Smaller input" />
            </TestCard>
            <TestCard title="Ghost">
              <Input label="Ghost" variant="ghost" placeholder="Ghost input" />
            </TestCard>
            <TestCard title="Quiet">
              <Input label="Quiet" variant="quiet" placeholder="Quiet input" />
            </TestCard>
            <TestCard title="Pill">
              <Input label="Pill" variant="secondary" pill placeholder="Pill input" />
            </TestCard>
            <TestCard title="Disabled">
              <Input label="Disabled" variant="quiet" disabled value="Disabled value" />
            </TestCard>
          </TestGrid>
        </Section>

        <Section title="Select Dropdown">
          <TestGrid>
            <TestCard>
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
            </TestCard>
            <TestCard>
              <Select
                label="With Hint"
                options={[
                  { value: "yes", label: "Yes" },
                  { value: "no", label: "No" },
                  { value: "maybe", label: "Maybe" },
                ]}
                hint="Select one of the options above"
              />
            </TestCard>
          </TestGrid>
        </Section>

        <Section title="Toggles">
          <TestGrid>
            <TestCard>
              <Toggle
                label="Enable notifications"
                checked={toggleStates.toggle1}
                onChange={(checked) => handleToggle("toggle1", checked)}
              />
            </TestCard>
            <TestCard>
              <Toggle
                label="Dark mode (enabled)"
                checked={toggleStates.toggle2}
                onChange={(checked) => handleToggle("toggle2", checked)}
              />
            </TestCard>
            <TestCard>
              <Toggle label="Disabled toggle" checked={false} onChange={() => {}} disabled />
            </TestCard>
            <TestCard>
              <Toggle
                label="With hint text"
                checked={toggleStates.toggle1}
                onChange={(checked) => handleToggle("toggle1", checked)}
                hint="This toggle has a helpful hint below"
              />
            </TestCard>
          </TestGrid>
        </Section>

        <Section title="Spinners">
          <TestGrid>
            <TestCard title="Small (16px)">
              <Spinner size={16} />
            </TestCard>
            <TestCard title="Medium (24px)">
              <Spinner size={24} />
            </TestCard>
            <TestCard title="Large (32px)">
              <Spinner size={32} />
            </TestCard>
            <TestCard title="Extra Large (48px)">
              <Spinner size={48} />
            </TestCard>
          </TestGrid>
        </Section>

        <Section title="Modal">
          <TestGrid>
            <TestCard>
              <Button variant="primary" onClick={() => setModalOpen(true)}>
                Open Modal
              </Button>
            </TestCard>
          </TestGrid>
        </Section>

        <Modal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          title="Test Modal"
          footer={
            <div className="flex justify-end gap-3">
              <Button variant="secondary" onClick={() => setModalOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={() => setModalOpen(false)}>
                Confirm
              </Button>
            </div>
          }
        >
          <div className="flex flex-col gap-4">
            <p>
              This is a test modal dialog. You can interact with all the UI components inside it.
            </p>
            <Input label="Modal Input" placeholder="Type something..." />
            <Select
              label="Modal Select"
              options={[
                { value: "opt1", label: "Option 1" },
                { value: "opt2", label: "Option 2" },
              ]}
            />
          </div>
        </Modal>
      </div>
    </div>
  );
}