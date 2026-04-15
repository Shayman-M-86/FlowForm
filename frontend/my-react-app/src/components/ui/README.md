# UI Components

This folder contains the reusable UI building blocks for `my-react-app`.

Use this file as a quick reference for:
- which components exist
- which props/variants they support
- copy-paste snippets you can drop into a page

## Shared Styling Files

These are styling-only helpers, not React components:

- `FormFieldShared.css`: shared field, label, hint, error, and control styles
- `InteractiveShared.css`: shared transitions, pill radius, and interactive surface styles

## Component Reference

| Component | Purpose | Key props |
| --- | --- | --- |
| `Button` | Actions and CTAs | `variant`, `size`, `pill`, `borderStyle` |
| `Input` | Single-line text input | `label`, `hint`, `error`, `variant`, `pill`, native input props |
| `LargeInput` | Multi-line textarea | `label`, `hint`, `error`, `size`, `maxText`, `showCount`, `autoGrow`, `maxAutoGrowHeight`, native textarea props |
| `Select` | Dropdown select | `label`, `options`, `hint`, native select props |
| `Toggle` | Boolean on/off control | `label`, `checked`, `onChange`, `disabled`, `hint` |
| `Tooltip` | Hover/focus label around another element | `title`, `size`, `children` |
| `Badge` | Small status label | `variant` |
| `Spinner` | Loading indicator | `size` |
| `Modal` | Dialog overlay | `open`, `onClose`, `title`, `footer`, `width` |
| `NumberStepper` | Increment/decrement one value | `value`, `onChange`, `min`, `max`, `step`, `size`, `pill`, `variant` |
| `NumberStepperGroup` | Increment/decrement multiple labeled values | `items`, `onChange`, `size`, `pill`, `variant` |

## Usage Snippets

### Button

Supported variants:
- `primary`
- `secondary`
- `danger`
- `ghost`
- `quiet`

Supported sizes:
- `md`
- `sm`
- `xs`

Supported border styles:
- `solid`
- `dotted`

```tsx
<Button variant="primary">Save</Button>
<Button variant="secondary" size="sm">Cancel</Button>
<Button variant="ghost" size="xs">Small Ghost</Button>
<Button variant="quiet" pill>Rounded Quiet</Button>
<Button variant="danger" borderStyle="dotted">Delete</Button>
```

### Input

Supported variants:
- `secondary`
- `ghost`
- `quiet`

```tsx
<Input label="Name" placeholder="Default" />
<Input label="Ghost" variant="ghost" placeholder="Ghost input" />
<Input label="Quiet" variant="quiet" placeholder="Quiet input" />
<Input label="Pill" variant="secondary" pill placeholder="Pill input" />
<Input label="Disabled" variant="quiet" disabled value="Disabled value" />
<Input label="Email" type="email" placeholder="email@example.com" hint="We only use this for login" />
<Input label="Password" type="password" error="Password is required" />
```

### LargeInput

Supported sizes:
- `sm`
- `md`
- `lg`

Additional large-input props:
- `maxText`
- `showCount`
- `autoGrow`
- `maxAutoGrowHeight`

You can also pass normal `textarea` props such as:
- `placeholder`
- `value`
- `defaultValue`
- `onChange`
- `rows`
- `disabled`
- `readOnly`
- `required`
- `name`

```tsx
<LargeInput
  label="Notes"
  size="md"
  placeholder="Write your notes..."
/>

<LargeInput
  label="Summary"
  size="lg"
  maxText={180}
  showCount
  placeholder="Write a concise summary..."
/>

<LargeInput
  label="Auto-Grow"
  size="sm"
  autoGrow
  maxAutoGrowHeight={220}
  placeholder="Type multiple lines..."
/>
```

### Select

`Select` takes an `options` array in the shape:

```tsx
[
  { value: "option1", label: "Option 1" },
  { value: "option2", label: "Option 2" },
]
```

```tsx
<Select
  label="Choose an option"
  options={[
    { value: "option1", label: "Option 1" },
    { value: "option2", label: "Option 2" },
  ]}
/>
```

### Toggle

```tsx
<Toggle
  label="Enable alerts"
  checked={enabled}
  onChange={setEnabled}
/>

<Toggle
  label="Email notifications"
  checked={emailEnabled}
  onChange={setEmailEnabled}
  hint="Used for submission updates"
/>
```

### Tooltip

Supported sizes:
- `sm`
- `md`
- `lg`

```tsx
<Tooltip title="Delete" size="sm">
  <Button variant="ghost">Small</Button>
</Tooltip>

<Tooltip title="Delete" size="md">
  <Button variant="ghost">Medium</Button>
</Tooltip>

<Tooltip title="Delete" size="lg">
  <Button variant="ghost">Large</Button>
</Tooltip>
```

### Badge

Supported variants:
- `default`
- `success`
- `danger`
- `warning`
- `accent`
- `muted`

```tsx
<Badge>Default</Badge>
<Badge variant="success">Success</Badge>
<Badge variant="danger">Danger</Badge>
<Badge variant="warning">Warning</Badge>
<Badge variant="accent">Accent</Badge>
<Badge variant="muted">Muted</Badge>
```

### Spinner

`Spinner` uses a numeric `size` in pixels.

```tsx
<Spinner />
<Spinner size={16} />
<Spinner size={28} />
```

### Modal

`Modal` supports:
- `open`
- `onClose`
- `title`
- `children`
- `footer`
- `width`

```tsx
<Modal
  open={modalOpen}
  onClose={() => setModalOpen(false)}
  title="Confirm action"
  width={480}
  footer={
    <>
      <Button variant="secondary" onClick={() => setModalOpen(false)}>
        Cancel
      </Button>
      <Button variant="primary" onClick={handleConfirm}>
        Confirm
      </Button>
    </>
  }
>
  <p>Are you sure you want to continue?</p>
</Modal>
```

### NumberStepper

Supported sizes:
- `sm`
- `xs`

Supported variants:
- `ghost`
- `secondary`

```tsx
<NumberStepper
  value={count}
  onChange={setCount}
  min={0}
  max={10}
  step={1}
/>

<NumberStepper
  value={count}
  onChange={setCount}
  size="xs"
  variant="secondary"
  pill
/>
```

### NumberStepperGroup

Each `items` entry supports:
- `key`
- `label`
- `value`
- `min`
- `max`
- `step`
- `disabled`

```tsx
<NumberStepperGroup
  size="sm"
  variant="secondary"
  items={[
    { key: "min", label: "Min", value: range.min, min: 0, max: 10 },
    { key: "max", label: "Max", value: range.max, min: 0, max: 10 },
  ]}
  onChange={(key, value) =>
    setRange((current) => ({ ...current, [key]: value }))
  }
/>
```

## Notes

- Most input-like components generate an `id` from `label` if you do not pass one.
- `Input` and `LargeInput` support normal DOM props from `input` and `textarea`.
- `Tooltip` wraps any child element, but it works best with controls such as buttons or icon triggers.
- `Modal` closes on `Escape` and click-outside.
- `NumberStepper` and `NumberStepperGroup` clamp values to `min` and `max` when provided.
