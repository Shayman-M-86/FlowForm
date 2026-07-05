// AI import feature — a self-contained, lazily-loadable unit.
//
// The Zod-based validator (surveyNodeImport) is only needed when a user pastes
// or generates survey JSON, so it is intentionally an internal dependency of
// this folder rather than part of the core builder. Consumers should load the
// whole feature on demand, e.g.:
//
//   const AiImportModal = lazy(() =>
//     import("../components/Utils/ai-import").then((m) => ({ default: m.AiImportModal }))
//   );
//
// Pulling in anything from here drags in `surveyNodeImport` (and zod) — that is
// by design and is why it lives behind a lazy boundary.

export { AiImportModal } from "./AiImportModal";
export { AiImportModal as default } from "./AiImportModal";

export type { SurveyNodeImportIssue } from "./surveyNodeImport";
export { SurveyNodeImportError } from "./surveyNodeImport";
