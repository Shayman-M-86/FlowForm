import { useEffect, useRef, useState } from "react";
import { Button, Modal } from "@flowform/ui";
import { AlertCircle, Check, ClipboardPaste, Copy, Sparkles } from "lucide-react";
import type { SurveyNode } from "../node/questionTypes";
import { findNodeLine, parseSurveyNodeJson, SurveyNodeImportError } from "./surveyNodeImport";

const AI_IMPORT_STORAGE_KEY = "flowform.ai-import.pending";

const SCHEMA_PROMPT = `You are a survey schema generator for FlowForm.

Return ONLY a JSON array of survey nodes — no explanation, no markdown, no code fences.

Each node is either a question node or a rule node.

QUESTION NODE
{ "type": "question", "sort_key": <number>, "content": <QuestionContent> }

QuestionContent shapes:

Choice (single or multi-select):
{ "id": "question_id_1", "title": "Section heading", "label": "Question text", "family": "choice", "definition": { "min": 1, "max": 1, "options": [{ "id": "opt_1", "label": "Option text" }] } }

Field (text / number / date):
{ "id": "question_id_1", "title": "Section heading", "label": "Question text", "family": "field", "definition": { "field_type": "short_text", "ui": { "placeholder": "Optional" } } }
field_type options: short_text | long_text | email | phone | number | date

Rating:
{ "id": "question_id_1", "title": "Section heading", "label": "Question text", "family": "rating", "definition": { "variant": "stars", "stars": 5, "ui": { "left_label": "Poor", "right_label": "Excellent" } } }
variant options: stars | slider | emoji

Matching:
{ "id": "question_id_1", "title": "Section heading", "label": "Question text", "family": "matching", "definition": { "prompts": [{ "id": "p1", "label": "Prompt" }], "matches": [{ "id": "m1", "label": "Match" }] } }

RULE NODE
{ "type": "rule", "sort_key": <number>, "content": { "id": "r1", "if": { "match": "ALL", "conditions": [{ "target_id": "question_id_1", "family": "choice", "requirements": { "required": ["opt_1"] } }] }, "then": { "do": { "skip_to": "question_id_3" } } } }

RULES
- All id values must be unique across the entire array
- Question ids: question_id_1, question_id_2, ...  Rule ids: r1, r2, ...
- sort_key: position × 100000 (first node = 100000)
- Only include "then.set", "then.do", "else" when needed

USER REQUEST
`;

interface AiImportModalProps {
  open: boolean;
  hasExistingQuestions: boolean;
  onClose: () => void;
  onImport: (nodes: SurveyNode[]) => void;
}

type Step = "describe" | "paste";

function loadPending(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(AI_IMPORT_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { description?: string };
    return typeof parsed.description === "string" ? parsed.description : null;
  } catch {
    return null;
  }
}

function savePending(description: string) {
  try { window.localStorage.setItem(AI_IMPORT_STORAGE_KEY, JSON.stringify({ description })); } catch { /* ignore */ }
}

function clearPending() {
  try { window.localStorage.removeItem(AI_IMPORT_STORAGE_KEY); } catch { /* ignore */ }
}

interface ValidationError {
  message: string;
  nodeIndex: number | null;
}

export function hasAiImportPending(): boolean {
  return loadPending() !== null;
}

export function AiImportModal({ open, hasExistingQuestions, onClose, onImport }: AiImportModalProps) {
  const pending = loadPending();
  const [step, setStep] = useState<Step>(pending ? "paste" : "describe");
  const [description, setDescription] = useState(pending ?? "");
  const [pasteValue, setPasteValue] = useState("");
  const [copied, setCopied] = useState(false);
  const [errorPromptCopied, setErrorPromptCopied] = useState(false);
  const [error, setError] = useState<ValidationError | null>(null);
  const [confirmReplace, setConfirmReplace] = useState(false);
  const [pendingNodes, setPendingNodes] = useState<SurveyNode[] | null>(null);
  const describeRef = useRef<HTMLTextAreaElement>(null);
  const pasteRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!open) return;
    const t = window.setTimeout(() => {
      (step === "describe" ? describeRef : pasteRef).current?.focus();
    }, 60);
    return () => window.clearTimeout(t);
  }, [open, step]);

  const prevPasteRef = useRef("");
  useEffect(() => {
    if (pasteValue !== "" && prevPasteRef.current !== pasteValue) setError(null);
    prevPasteRef.current = pasteValue;
  }, [pasteValue]);

  async function handleCopy() {
    const text = `${SCHEMA_PROMPT}${description.trim()}`;
    try { await navigator.clipboard.writeText(text); } catch { /* ignore */ }
    savePending(description);
    setCopied(true);
    setStep("paste");
    setPasteValue("");
    window.setTimeout(() => setCopied(false), 2000);
  }

  function handleImport() {
    setError(null);
    const rawJson = pasteValue.trim();
    let nodes: SurveyNode[];
    try {
      nodes = parseSurveyNodeJson(rawJson);
    } catch (e) {
      const importError = e instanceof SurveyNodeImportError ? e : null;
      const line = findNodeLine(rawJson, importError?.nodeIndex ?? null);
      setError({
        message: importError?.message ?? "Invalid survey structure.",
        nodeIndex: line,
      });
      setPasteValue("");
      return;
    }
    if (hasExistingQuestions) {
      setPendingNodes(nodes);
      setConfirmReplace(true);
    } else {
      finish(nodes);
    }
  }

  function finish(nodes: SurveyNode[]) {
    clearPending();
    setStep("describe");
    setDescription("");
    setPasteValue("");
    setError(null);
    setPendingNodes(null);
    setConfirmReplace(false);
    onImport(nodes);
  }

  function handleClose() {
    setError(null);
    setConfirmReplace(false);
    setPendingNodes(null);
    onClose();
  }

  function handleStartOver() {
    clearPending();
    setStep("describe");
    setPasteValue("");
    setError(null);
    setConfirmReplace(false);
    setPendingNodes(null);
  }

  const footer = (
    <div className="flex w-full items-center justify-between">
      {step === "paste" ? (
        <Button type="button" variant="ghost" size="sm" onClick={handleStartOver}>
          ← Start over
        </Button>
      ) : (
        <span />
      )}
      <div className="flex gap-2">
        <Button type="button" variant="ghost" size="sm" onClick={handleClose}>
          Cancel
        </Button>
        {step === "describe" ? (
          <>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setStep("paste")}
            >
              <ClipboardPaste size={13} aria-hidden="true" /> Skip to paste
            </Button>
            <Button
              type="button"
              variant="primary"
              size="sm"
              disabled={!description.trim()}
              onClick={handleCopy}
            >
              {copied ? (
                <>Copied!</>
              ) : (
                <><Copy size={13} aria-hidden="true" /> Copy prompt</>
              )}
            </Button>
          </>
        ) : (
          <Button
            type="button"
            variant="primary"
            size="sm"
            disabled={!pasteValue.trim() || confirmReplace}
            onClick={handleImport}
          >
            <ClipboardPaste size={13} aria-hidden="true" /> Import
          </Button>
        )}
      </div>
    </div>
  );

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title={step === "describe" ? "Generate with AI" : "Paste AI response"}
      footer={footer}
      width={600}
      className="min-h-[420px] w-full min-w-[min(320px,calc(100vw-40px))]"
      bodyClassName={step === "paste" ? "pb-1.5" : "pb-9.5"}
    >
      {step === "describe" ? (
        <div className="flex flex-1 flex-col gap-4">
          <div className="flex items-start gap-2.5 rounded-lg border border-border bg-muted/40 px-3.5 py-3">
            <Sparkles size={15} className="mt-0.5 shrink-0 text-primary" aria-hidden="true" />
            <p className="m-0 text-sm text-muted-foreground">
              Describe your survey. Click <strong className="text-foreground font-medium">Copy prompt</strong> — then paste into any AI assistant and bring back the JSON.
            </p>
          </div>
          <textarea
            ref={describeRef}
            className="flex-1 w-full resize-none rounded-lg border border-border bg-background px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="e.g. A 6-question customer satisfaction survey — a star rating, two multiple choice questions about product features, an email field, an open feedback box, and a rule that skips feedback if rating is 4 or above."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
      ) : (
        <div className="flex flex-1 flex-col gap-2">
          <div className="flex items-start gap-2.5 mb-2 rounded-lg border border-border bg-muted/40 px-3.5 py-3">
            <ClipboardPaste size={15} className="mt-0.5 shrink-0 text-primary" aria-hidden="true" />
            <p className="m-0 text-sm text-muted-foreground">
              Paste the JSON array your AI returned. The builder validates the structure before importing.
            </p>
          </div>
          <textarea
            ref={pasteRef}
            className="flex-1 w-full resize-none rounded-lg border border-border bg-background px-3 py-2.5 font-mono text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder={'[{ "type": "question", "sort_key": 100000, ... }]'}
            value={pasteValue}
            onChange={(e) => setPasteValue(e.target.value)}
            spellCheck={false}
          />
          {!error && (
            <div className="flex justify-end">
              <span
                className="pointer-events-none flex items-center gap-1.5 rounded-md bg-green-500/10 px-2.5 py-1 text-xs font-medium text-green-600 shadow-sm ring-1 ring-green-500/30 transition-all duration-200 dark:text-green-400"
                style={{ opacity: copied ? 1 : 0, transform: copied ? "translateY(0)" : "translateY(4px)" }}
                aria-live="polite"
              >
                <Check size={11} aria-hidden="true" />
                Copied
              </span>
            </div>
          )}
          {error && (() => {
            const fixPrompt = `The JSON you gave me has a validation error: "${error.message}". Fix the issue and return the complete corrected JSON array — no explanation, no markdown.`;
            return (
              <div className="rounded-lg border border-destructive/30 bg-destructive/8 overflow-hidden">
                <div className="flex items-start gap-2.5 px-3.5 py-3">
                  <AlertCircle size={14} className="mt-0.5 shrink-0 text-destructive" aria-hidden="true" />
                  <div className="flex flex-col gap-0.5 min-w-0">
                    <p className="m-0 text-xs font-semibold text-destructive">
                      Validation error{error.nodeIndex !== null ? <span className="ml-1.5 font-normal opacity-60">line {error.nodeIndex}</span> : null}
                    </p>
                    <p className="m-0 text-xs text-destructive/80">{error.message}</p>
                  </div>
                </div>
                <div className="flex items-center justify-between border-t border-destructive/20 bg-destructive/5 px-3.5 py-2">
                  <p className="m-0 text-xs text-muted-foreground">Copy a fix prompt for your AI assistant</p>
                  <Button
                    type="button"
                    bare
                    variant="secondary"
                    size="xs"
                    className="text-green-600 hover:text-green-700 dark:text-green-400 dark:hover:text-green-300"
                    icon={errorPromptCopied ? "check" : "copy"}
                    onClick={async () => {
                      try {
                        await navigator.clipboard.writeText(fixPrompt);
                        setErrorPromptCopied(true);
                        window.setTimeout(() => setErrorPromptCopied(false), 2000);
                      } catch { /* ignore */ }
                    }}
                  >
                    {errorPromptCopied ? "Copied" : "Copy"}
                  </Button>
                </div>
              </div>
            );
          })()}
          {confirmReplace && (
            <div className="flex items-center justify-between rounded-lg border border-border bg-muted/40 px-3.5 py-3">
              <p className="m-0 text-sm text-foreground">Replace existing questions?</p>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="destructive"
                  size="sm"
                  onClick={() => pendingNodes && finish(pendingNodes)}
                >
                  Replace
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => { setConfirmReplace(false); setPendingNodes(null); }}
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}
