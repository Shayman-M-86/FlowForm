import { useCallback, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { useParams, useSearchParams } from "react-router-dom";
import {
  createLinkSubmission,
  createSlugSubmission,
  getPublicSurvey,
  resolveToken,
} from "../api/public";
import type { AnswerIn, PublicSurveyOut, ResolveLinkOut } from "../api/types";
import { Button, Spinner } from "../index.optimized";
import { useFetch } from "../hooks/useFetch";
import { hasSubmitted, markSubmitted, surveyKey, tokenKey } from "../hooks/useSubmissionGuard";
import "./QuizTakerPage.css";

interface QuizTakerPageProps {
  mode: "slug" | "token";
}

// ── Spec-compliant schema types ───────────────────────────────────────────────

interface OptionItem  { id: string; label: string }
interface MatchItem   { id: string; label: string }

// ── Individual question renderers ─────────────────────────────────────────────

interface QuestionRendererProps {
  schema: Record<string, unknown>;
  questionKey: string;
  value: unknown;
  onChange: (value: unknown) => void;
}

function QuestionRenderer({ schema, questionKey, value, onChange }: QuestionRendererProps) {
  if (!schema) return null;

  const family = schema.family as string;
  const label  = (schema.label as string) ?? questionKey;
  const inner  = (schema.schema as Record<string, unknown>) ?? {};
  const ui     = (schema.ui    as Record<string, unknown>) ?? {};

  return (
    <div className="quiz-question">
      <div className="quiz-question__label">{label}</div>

      {/* ── Choice ── */}
      {family === "choice" && (() => {
        const opts = (inner.options as OptionItem[]) ?? [];
        const maxSelected = (inner.max_selected as number) ?? 1;
        const isMulti = maxSelected > 1 || (ui.style as string) === "checkbox";

        if (isMulti) {
          const selected = (value as string[]) ?? [];
          return (
            <div className="quiz-choices">
              {opts.map((opt) => (
                <label key={opt.id} className="quiz-choice">
                  <input
                    type="checkbox"
                    name={questionKey}
                    value={opt.id}
                    checked={selected.includes(opt.id)}
                    onChange={() => {
                      const next = selected.includes(opt.id)
                        ? selected.filter((id) => id !== opt.id)
                        : [...selected, opt.id];
                      onChange(next);
                    }}
                  />
                  <span>{opt.label}</span>
                </label>
              ))}
            </div>
          );
        }

        return (
          <div className="quiz-choices">
            {opts.map((opt) => (
              <label key={opt.id} className="quiz-choice">
                <input
                  type="radio"
                  name={questionKey}
                  value={opt.id}
                  checked={value === opt.id}
                  onChange={() => onChange(opt.id)}
                />
                <span>{opt.label}</span>
              </label>
            ))}
          </div>
        );
      })()}

      {/* ── Field ── */}
      {family === "field" && (
        <input
          className="quiz-field-input"
          type={(inner.field_type as string) ?? "text"}
          value={(value as string) ?? ""}
          onChange={(e) => onChange(e.target.value)}
          placeholder={(ui.placeholder as string) ?? "Your answer"}
        />
      )}

      {/* ── Rating ── */}
      {family === "rating" && (() => {
        const min = (inner.min as number) ?? 1;
        const max = (inner.max as number) ?? 5;
        return (
          <div className="quiz-rating">
            {Array.from({ length: max - min + 1 }, (_, i) => i + min).map((n) => (
              <button
                key={n}
                type="button"
                className={`quiz-rating__btn ${value === n ? "quiz-rating__btn--active" : ""}`}
                onClick={() => onChange(n)}
              >
                {n}
              </button>
            ))}
          </div>
        );
      })()}

      {/* ── Matching ── */}
      {family === "matching" && (() => {
        const leftItems  = (inner.left_items  as MatchItem[]) ?? [];
        const rightItems = (inner.right_items as MatchItem[]) ?? [];
        const matches    = (value as Record<string, string>) ?? {};

        return (
          <div className="quiz-matching">
            {leftItems.map((lItem) => (
              <div key={lItem.id} className="quiz-matching__row">
                <span className="quiz-matching__left">{lItem.label}</span>
                <span className="quiz-matching__arrow">→</span>
                <select
                  className="quiz-matching__select"
                  value={matches[lItem.id] ?? ""}
                  onChange={(e) => onChange({ ...matches, [lItem.id]: e.target.value })}
                >
                  <option value="">Select…</option>
                  {rightItems.map((rItem) => (
                    <option key={rItem.id} value={rItem.id}>{rItem.label}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        );
      })()}
    </div>
  );
}

// ── Build spec-compliant answer_value from raw answer state ───────────────────

function buildAnswerValue(
  family: string,
  rawValue: unknown,
  _schema: Record<string, unknown>,
): Record<string, unknown> {
  switch (family) {
    case "choice": {
      const selected = Array.isArray(rawValue) ? rawValue : rawValue != null ? [rawValue] : [];
      return { selected };
    }
    case "field":
      return { value: rawValue ?? "" };
    case "rating":
      return { value: rawValue ?? null };
    case "matching": {
      const matchMap = (rawValue as Record<string, string>) ?? {};
      const matches = Object.entries(matchMap)
        .filter(([, rightId]) => rightId)
        .map(([leftId, rightId]) => ({ left_id: leftId, right_id: rightId }));
      return { matches };
    }
    default:
      return { value: rawValue };
  }
}

// ── Quiz form ─────────────────────────────────────────────────────────────────

interface QuizFormProps {
  survey: PublicSurveyOut | ResolveLinkOut;
  guardKey: string;
  /** Called with the built answer list; should return a promise that resolves on success. */
  onSubmit: (answers: AnswerIn[], versionId: number) => Promise<void>;
  /** Whether a submission mechanism is available (false = preview mode). */
  canSubmit: boolean;
}

function QuizForm({ survey, guardKey, onSubmit, canSubmit }: QuizFormProps) {
  const surveyData = "survey" in survey ? survey.survey : null;
  const version    = "published_version" in survey ? survey.published_version : null;
  const questions  = version?.compiled_schema?.questions ?? [];

  const [answers,     setAnswers]     = useState<Record<string, unknown>>({});
  const [submitting,  setSubmitting]  = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitted,   setSubmitted]   = useState(() => hasSubmitted(guardKey));

  function setAnswer(key: string, value: unknown) {
    setAnswers((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!version) return;
    setSubmitting(true);
    setSubmitError(null);

    const answerList: AnswerIn[] = questions
      .filter((q) => q.question_key && q.question_schema)
      .map((q) => {
        const qSchema = q.question_schema as Record<string, unknown>;
        const family  = (qSchema.family as string) ?? "field";
        return {
          question_key: q.question_key,
          answer_family: family,
          answer_value: buildAnswerValue(family, answers[q.question_key], qSchema),
        };
      });

    try {
      await onSubmit(answerList, version.id);
      markSubmitted(guardKey);
      setSubmitted(true);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Submission failed.");
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <div className="quiz-thankyou">
        <div className="quiz-thankyou__icon">✓</div>
        <h2>Already submitted</h2>
        <p>You have already completed {surveyData?.title ?? "this survey"} in this browser.</p>
      </div>
    );
  }

  if (!version) {
    return <div className="quiz-error">This survey has no published version yet.</div>;
  }

  return (
    <form className="quiz-form" onSubmit={handleSubmit}>
      <h1 className="quiz-title">{surveyData?.title ?? "Quiz"}</h1>
      {questions.length === 0 ? (
        <p className="quiz-no-questions">No questions in this quiz.</p>
      ) : (
        questions.map((q) => (
          <QuestionRenderer
            key={q.id}
            schema={q.question_schema as Record<string, unknown>}
            questionKey={q.question_key}
            value={answers[q.question_key]}
            onChange={(v) => setAnswer(q.question_key, v)}
          />
        ))
      )}

      {submitError && (
        <div className="quiz-inline-error">{submitError}</div>
      )}

      {canSubmit ? (
        <Button type="submit" variant="primary" disabled={submitting}>
          {submitting ? "Submitting…" : "Submit"}
        </Button>
      ) : (
        <p className="quiz-preview-note">
          Preview mode — submission requires a public link token.
        </p>
      )}
    </form>
  );
}

// ── Page: slug mode (no auth required) ───────────────────────────────────────

function SlugQuizPage({ slug }: { slug: string }) {
  const { isAuthenticated, getAccessTokenSilently } = useAuth0();
  const fetcher = useCallback(() => getPublicSurvey(slug), [slug]);
  const { data, loading, error } = useFetch(fetcher, [slug]);

  const handleSubmit = useCallback(async (answers: AnswerIn[], versionId: number) => {
    let authHeaders: HeadersInit | undefined;
    if (isAuthenticated) {
      const accessToken = await getAccessTokenSilently({
        authorizationParams: { audience: import.meta.env.VITE_AUTH0_AUDIENCE },
      });
      authHeaders = { Authorization: `Bearer ${accessToken}` };
    }

    await createSlugSubmission({
      public_slug: slug,
      survey_version_id: versionId,
      answers,
      started_at: new Date().toISOString(),
      submitted_at: new Date().toISOString(),
    }, authHeaders);
  }, [slug, isAuthenticated, getAccessTokenSilently]);

  if (loading) return <div className="quiz-loading"><Spinner /></div>;
  if (error)   return <div className="quiz-error">{error}</div>;
  if (!data)   return null;

  const canSubmit = data.published_version !== null;

  return (
    <QuizForm
      survey={data}
      guardKey={surveyKey(data.survey.id)}
      onSubmit={handleSubmit}
      canSubmit={canSubmit}
    />
  );
}

// ── Page: token mode (auth required) ─────────────────────────────────────────

function TokenQuizPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const { isLoading, isAuthenticated, loginWithRedirect, getAccessTokenSilently } = useAuth0();

  const fetcher = useCallback(async () => {
    if (!token) throw new Error("No token provided.");
    const accessToken = await getAccessTokenSilently({
      authorizationParams: { audience: import.meta.env.VITE_AUTH0_AUDIENCE },
    });
    return resolveToken(token, { Authorization: `Bearer ${accessToken}` });
  }, [token, getAccessTokenSilently]);

  const { data, loading, error } = useFetch(isAuthenticated ? fetcher : null, [token, isAuthenticated]);

  const handleSubmit = useCallback(async (answers: AnswerIn[], versionId: number) => {
    const accessToken = await getAccessTokenSilently({
      authorizationParams: { audience: import.meta.env.VITE_AUTH0_AUDIENCE },
    });
    await createLinkSubmission(
      {
        token,
        survey_version_id: versionId,
        answers,
        started_at: new Date().toISOString(),
        submitted_at: new Date().toISOString(),
      },
      { Authorization: `Bearer ${accessToken}` },
    );
  }, [token, getAccessTokenSilently]);

  if (!token) return <div className="quiz-error">No token provided in URL (?token=…).</div>;

  if (isLoading) return <div className="quiz-loading"><Spinner /></div>;

  if (!isAuthenticated) {
    return (
      <div className="quiz-auth-gate">
        <p>You need to sign in to access this survey link.</p>
        <Button
          variant="primary"
          onClick={() => loginWithRedirect({
            appState: { returnTo: `${window.location.pathname}${window.location.search}` },
          })}
        >
          Sign in to continue
        </Button>
      </div>
    );
  }

  if (loading) return <div className="quiz-loading"><Spinner /></div>;
  if (error)   return <div className="quiz-error">{error}</div>;
  if (!data)   return null;

  if (!data.link.is_active)
    return <div className="quiz-error">This link is no longer active.</div>;
  if (data.link.expires_at && new Date(data.link.expires_at) < new Date())
    return <div className="quiz-error">This link has expired.</div>;

  return (
    <QuizForm
      survey={data}
      guardKey={tokenKey(data.link.token_prefix)}
      onSubmit={handleSubmit}
      canSubmit={true}
    />
  );
}

// ── Top-level export ──────────────────────────────────────────────────────────

export function QuizTakerPage({ mode }: QuizTakerPageProps) {
  const { publicSlug } = useParams<{ publicSlug?: string }>();

  return (
    <div className="quiz-shell">
      <div className="quiz-container">
        {mode === "slug" && publicSlug ? (
          <SlugQuizPage slug={publicSlug} />
        ) : (
          <TokenQuizPage />
        )}
      </div>
    </div>
  );
}
