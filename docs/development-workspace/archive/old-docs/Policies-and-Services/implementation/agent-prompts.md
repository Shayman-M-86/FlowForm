# Agent Prompt Bank

Each prompt is appended to the session-start output automatically. It contains
only what is unique to that target — stop conditions and scope constraints.

---

## Target 01 Prompt: Runtime Inventory

```text
Do not edit code. Produce: context pack, route → service → repository flow map,
hidden or stale consumers, first contract that should change, pass report.
```

---

## Target 02 Prompt: AccessGrant Contract

```text
Stop if subject resolution or token mechanics need redesign.
Implement only AccessGrant contract changes and focused tests for this pass.
```

---

## Target 03 Prompt: RecognitionTokenLookupResult

```text
Stop if canonical subject helper behavior must be designed before token lookup can be fixed.
Implement only RecognitionTokenLookupResult behavior and focused tests for this pass.
```

---

## Target 04 Prompt: SubjectResolutionResult

```text
Stop if AccessGrant still lacks required access or assigned-subject context.
Implement only SubjectResolutionResult behavior and focused tests for this pass.
```

---

## Target 05 Prompt: TokenActionResult and Token Mechanics

```text
Stop if SubjectResolutionResult does not return enough token-action data.
Implement only token action mechanics and focused tests for this pass.
```

---

## Target 06 Prompt: SessionStart Orchestration

```text
Stop if transaction boundary needs redesign beyond this pass.
Implement only SessionStart orchestration changes and focused tests for this pass.
```

---

## Target 07 Prompt: Transaction Boundary

```text
Stop if repository flush behavior prevents coherent rollback plan.
Stop and ask before any migration or destructive database change.
Implement only transaction-boundary changes and focused tests for this pass.
```

---

## Target 08 Prompt: Authenticated Account-Linking

```text
Stop if response/cookie route contract needs redesign first.
Implement only authenticated account-linking behavior and focused tests for this pass.
```

---

## Target 09 Prompt: Response and Cookie Contract

```text
Stop and ask before editing if API contract decision needs user approval.
Implement only response/cookie contract changes and focused tests for this pass.
```

---

## Target 10 Prompt: Flow Matrix Tests

```text
Stop if tests need behavior changes not yet implemented by earlier targets.
Implement only flow-matrix tests and focused test support for this pass.
```

---

## Target 11 Prompt: Delete or Quarantine Stale Old Modules

```text
Stop if hidden consumers still import old modules.
Do not delete modules unless local plan proves no current consumer needs them.
Implement only stale-module quarantine/deletion and focused tests for this pass.
```

---

## Target 12 Prompt: Docstring Cleanup

```text
Do not change behavior in this pass.
Implement only docstring/comment cleanup for this pass.
```

---

## Target 13 Prompt: Implementation Summary

```text
Do not change any code or tests in this pass.
Read pass reports 01–12, the flow matrix, and the current service code.
Produce a summary report covering:
  - what each flow matrix row now has working end-to-end
  - what is partially implemented (logic present but untested, or tested but code missing)
  - what is not yet started (policy doc requires it, no code exists)
  - any places where current code disagrees with the policy docs
Write the report to pass-reports/13-implementation-summary.md and stop.
```
