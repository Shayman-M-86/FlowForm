# @flowform/ui — Component Reference

All imports from `@flowform/ui`.

---

## Theme

```tsx
<ThemeProvider>          // wrap app root — required for useTheme / ThemeToggle
useTheme()               // → { theme: 'light' | 'dark', toggleTheme: () => void }
<ThemeToggle />          // ready-made sun/moon button, uses useTheme internally
```

---

## Button

```tsx
<Button
  variant?="primary | secondary | danger | ghost"   // default: secondary
  size?="xxs | xs | sm | md | lg | xl"              // default: md
  pill?={boolean}                                    // default: false
  borderStyle?="solid | dotted"                      // default: solid
  disabled?={boolean}
  // + all native <button> props
>
  children
</Button>
```

---

## Input

```tsx
<Input
  label?="string"
  hint?="string"
  error?="string"
  variant?="secondary | ghost | quiet"   // default: secondary
  size?="xxs | xs | sm | md | lg | xl"  // default: md
  pill?={boolean}                        // default: false
  // + all native <input> props (except size)
/>
```

---

## LargeInput (textarea)

```tsx
<LargeInput
  label?="string"
  hint?="string"
  error?="string"
  variant?="secondary | ghost | quiet"   // default: secondary
  size?="sm | md | lg"                   // default: md — controls min/max height
  maxText?={number}                      // maxLength
  showCount?={boolean}                   // show currentLength/maxText counter
  autoGrow?={boolean}                    // auto-expand to fit content
  maxAutoGrowHeight?={number}            // px cap when autoGrow=true
  shellClassName?="string"               // className on the outer shell div
  // + all native <textarea> props
/>
```

---

## Select

```tsx
<Select
  options={[{ value: string, label: string }]}
  value?="string"                        // controlled
  defaultValue?="string"                 // uncontrolled
  placeholder?="string"
  label?="string"
  hint?="string"
  error?="string"
  variant?="secondary | ghost | quiet"   // default: secondary
  size?="xxs | xs | sm | md | lg | xl"  // default: md
  pill?={boolean}
  disabled?={boolean}
  name?="string"                         // renders hidden <input> for forms
  onChange?={(e) => void}               // e.target.value / e.currentTarget.value
  onValueChange?={(value: string) => void}
/>
```

---

## Card / CardRow / CardStack

```tsx
<Card
  size?="xs | sm | md | lg | xl"              // default: md — controls padding + shadow
  tone?="default | muted | ghost"             // default: default
  className?="string"
>

<CardRow
  gap?="xs | sm | md | lg | xl"   // default: md
  wrap?={boolean}                  // default: true
  className?="string"
>

<CardStack
  gap?="xs | sm | md | lg | xl"   // default: md
  className?="string"
>
```

---

## Modal

```tsx
<Modal
  open={boolean}
  onClose={() => void}
  title="string"
  footer?={ReactNode}    // renders in modal footer, right-aligned
  width?={number}        // max-width in px, default: 480
>
  children               // renders in scrollable modal body
</Modal>
```

Closes on Escape key and backdrop click.

---

## NumberStepper

```tsx
<NumberStepper
  value={number}
  onChange={(value: number) => void}
  min?={number}
  max?={number}
  step?={number}                              // default: 1
  size?="xs | sm"                             // default: sm
  variant?="primary | secondary | ghost"      // default: primary
  pill?={boolean}
  allowInput?={boolean}                       // show editable input instead of static value
  disabled?={boolean}
  ariaLabel?="string"
/>
```

---

## NumberStepperGroup

```tsx
<NumberStepperGroup
  items={[{
    key: string,
    label: string,
    value: number,
    min?: number,
    max?: number,
    step?: number,
    disabled?: boolean,
  }]}
  onChange={(key: string, value: number) => void}
  size?="xs | sm"
  variant?="primary | secondary | ghost"
  pill?={boolean}
  allowInput?={boolean}
  ariaLabel?="string"
/>
```

---

## Badge

```tsx
<Badge
  variant?="default | success | danger | warning | accent | muted"   // default: default
  size?="xxs | xs | sm | md | lg | xl"                               // default: xs
>
  children
</Badge>
```

---

## Toggle

```tsx
<Toggle
  label="string"
  checked={boolean}
  onChange={(checked: boolean) => void}
  disabled?={boolean}
  hint?="string"
/>
```

---

## Spinner

```tsx
<Spinner size?={number} />   // size = px diameter, default: 20
```

---

## Tooltip

```tsx
<Tooltip
  title="string"             // tooltip text
  size?="sm | md | lg"       // default: md
  className?="string"
>
  {/* trigger element */}
</Tooltip>
```

Renders above trigger via portal. Shows on hover/focus.

---

## ExpandableTextArea

Auto-growing textarea in a bordered shell.

```tsx
<ExpandableTextArea
  value="string"
  onChange={(value: string) => void}
  readOnly?={boolean}
  placeholder?="string"
  maxLength?={number}
  minHeightClassName?="string"   // default: "min-h-[46px]"
  maxHeightClassName?="string"   // default: "max-h-[200px]"
  maxHeightPx?={number}          // default: 200 — scroll threshold
  className?="string"
  textareaClassName?="string"
/>
```

---

## ExpandableSelector

Like ExpandableTextArea but with a circular select-indicator button on the left.

```tsx
<ExpandableSelector
  value="string"
  onChange={(value: string) => void}
  selected?={boolean}
  readOnly?={boolean}
  placeholder?="string"
  maxLength?={number}
  minHeightClassName?="string"
  maxHeightClassName?="string"
  onSelect?={() => void}         // fired when indicator button is clicked
  className?="string"
  textareaClassName?="string"
/>
```

---

## Exported style helpers (advanced use)

Use these when composing custom inputs that need to match the standard control look.

```tsx
// Class name builders
getInputControlClassName({ size, variant, pill, error, className? })
getSurfaceClassName({ variant, focusMode: 'focus'|'focus-within', pill?, error?, extra? })
getTextareaShellClassName({ variant, error })
stepperShellClass({ size, variant, pill })
stepperButtonClass({ size, variant, pill })
stepperValueClass(size)
stepperInputClass(size)

// Raw class string maps (index by size key)
controlSizeClasses     // ControlSize → height/padding/text classes
badgeSizeClasses       // ControlSize → badge padding/text classes
cardPaddingClasses     // ControlSize → padding class
stackGapClasses        // ControlSize → gap class
textareaSizeClasses    // TextareaSize → fixed min/max height + padding
textareaBodySizeClasses // TextareaSize → padding + text (for autoGrow)
textareaMinHeights     // TextareaSize → number (px)

// CSS class name constants
formFieldClass      // "ui-field"
formLabelClass      // "ui-label"
formHintClass       // "ui-hint"
formErrorClass      // "ui-error"
controlBaseClass    // "ui-control-base"

// Types
type ControlSize = "xxs" | "xs" | "sm" | "md" | "lg" | "xl"
type TextareaSize = "sm" | "md" | "lg"
type InputVariant = "secondary" | "ghost" | "quiet"
type FocusMode = "focus" | "focus-within"
type StepperSize = "xs" | "sm"
type StepperVariant = "primary" | "secondary" | "ghost"
type Theme = "light" | "dark"
type SelectChangeEvent  // { target: { value, name? }, currentTarget: { value, name? } }
```
