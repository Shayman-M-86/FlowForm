import { useEffect, useRef, useState } from "react";
import { Button, Modal } from "@flowform/ui";
import { AlertCircle, Check, ClipboardPaste, Copy, Sparkles } from "lucide-react";
import type { SurveyNode } from "../../node/questionTypes";
import {
  findNodeLine,
  parseSurveyNodeJson,
  SurveyNodeImportError,
  type SurveyNodeImportIssue,
} from "./surveyNodeImport";

import { buildSurveyNodePrompt, buildSurveyNodeFixPrompt } from "./surveyNodePrompt";

const AI_IMPORT_STORAGE_KEY = "flowform.ai-import.pending";

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
  issues: SurveyNodeImportIssue[];
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
    const text = buildSurveyNodePrompt(description);
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
      const issues = importError
        ? importError.issues.map((issue) => ({
            ...issue,
            line: issue.line ?? findNodeLine(rawJson, issue.nodeIndex),
          }))
        : [{
            path: "$",
            message: "Invalid survey structure.",
            nodeIndex: null,
            line: null,
            column: null,
          }];
      setError({
        message: importError?.message ?? "Invalid survey structure.",
        issues,
      });
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
              Describe your survey. Click <strong className="text-foreground font-medium">Copy prompt</strong> to include the complete schema and examples — then paste into any AI assistant and bring back the JSON.
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
            placeholder="Paste the complete JSON array from your AI assistant"
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
            const fixPrompt = buildSurveyNodeFixPrompt(pasteValue, error.issues, description);
            const visibleIssues = error.issues.slice(0, 8);
            const hiddenCount = error.issues.length - visibleIssues.length;
            return (
              <div className="rounded-lg border border-destructive/30 bg-destructive/8 overflow-hidden">
                <div className="flex items-start gap-2.5 px-3.5 py-3">
                  <AlertCircle size={14} className="mt-0.5 shrink-0 text-destructive" aria-hidden="true" />
                  <div className="flex min-w-0 flex-col gap-2">
                    <p className="m-0 text-xs font-semibold text-destructive">
                      {error.issues.length === 1 ? "Validation error" : `${error.issues.length} validation errors`}
                    </p>
                    <ul className="m-0 flex max-h-44 flex-col gap-2 overflow-auto p-0 text-xs text-destructive/85">
                      {visibleIssues.map((issue, index) => (
                        <li key={`${issue.path}-${index}`} className="list-none">
                          <div className="font-mono text-[11px] font-semibold text-destructive">
                            {issue.path}
                            {issue.line ? (
                              <span className="ml-1.5 font-sans font-normal opacity-70">
                                line {issue.line}{issue.column ? `, col ${issue.column}` : ""}
                              </span>
                            ) : issue.nodeIndex !== null ? (
                              <span className="ml-1.5 font-sans font-normal opacity-70">
                                node {issue.nodeIndex}
                              </span>
                            ) : null}
                          </div>
                          <div>{issue.message}</div>
                          {issue.suggestion ? (
                            <div className="mt-0.5 text-destructive/70">{issue.suggestion}</div>
                          ) : null}
                        </li>
                      ))}
                      {hiddenCount > 0 ? (
                        <li className="list-none text-destructive/70">
                          {hiddenCount} more error{hiddenCount === 1 ? "" : "s"} hidden. Copy the fix prompt for the full list.
                        </li>
                      ) : null}
                    </ul>
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
