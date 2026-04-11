import { useCallback, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { createPublicSubmission, getPublicSurvey, resolveToken } from "../api/public";
import type { AnswerIn, PublicSurveyOut, ResolveLinkOut } from "../api/types";
import { Button } from "../components/ui/Button";
import { Spinner } from "../components/ui/Spinner";
import { useFetch } from "../hooks/useFetch";
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

        // single-select radio
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
      // rawValue is string (single) or string[] (multi)
      const selected = Array.isArray(rawValue) ? rawValue : rawValue != null ? [rawValue] : [];
      return { selected };
    }
    case "field":
      return { value: rawValue ?? "" };
    case "rating":
      return { value: rawValue ?? null };
    case "matching": {
      // rawValue is Record<leftId, rightId>
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
  token?: string;
}

function QuizForm({ survey, token }: QuizFormProps) {
  const surveyData = "survey" in survey ? survey.survey : null;
  const version    = "published_version" in survey ? survey.published_version : null;
  const questions  = version?.compiled_schema?.questions ?? [];

  const [answers,     setAnswers]     = useState<Record<string, unknown>>({});
  const [submitting,  setSubmitting]  = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitted,   setSubmitted]   = useState(false);

  function setAnswer(key: string, value: unknown) {
    setAnswers((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!version || !token) return;
    setSubmitting(true);
    setSubmitError(null);

    const answerList: AnswerIn[] = questions
      .filter((q) => q.question_key && q.question_schema)
      .map((q) => {
        const qSchema = q.question_schema as Record<string, unknown>;
        const family  = (qSchema.family as string) ?? "field";
        const rawValue = answers[q.question_key];
        return {
          question_key: q.question_key,
          answer_family: family,
          answer_value: buildAnswerValue(family, rawValue, qSchema),
        };
      });

    try {
      await createPublicSubmission({
        public_token: token,
        survey_version_id: version.id,
        is_anonymous: true,
        answers: answerList,
        started_at: new Date().toISOString(),
        submitted_at: new Date().toISOString(),
      });
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
        <h2>Response submitted!</h2>
        <p>Thank you for completing {surveyData?.title ?? "this quiz"}.</p>
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

      {token ? (
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

// ── Page: slug mode ───────────────────────────────────────────────────────────

function SlugQuizPage({ slug }: { slug: string }) {
  const fetcher = useCallback(() => getPublicSurvey(slug), [slug]);
  const { data, loading, error } = useFetch(fetcher, [slug]);

  if (loading) return <div className="quiz-loading"><Spinner /></div>;
  if (error)   return <div className="quiz-error">{error}</div>;
  if (!data)   return null;

  return <QuizForm survey={data} />;
}

// ── Page: token mode ──────────────────────────────────────────────────────────

function TokenQuizPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const fetcher = useCallback(
    () => (token ? resolveToken(token) : Promise.reject(new Error("No token provided."))),
    [token],
  );
  const { data, loading, error } = useFetch(token ? fetcher : null, [token]);

  if (!token) return <div className="quiz-error">No token provided in URL (?token=…).</div>;
  if (loading) return <div className="quiz-loading"><Spinner /></div>;
  if (error)   return <div className="quiz-error">{error}</div>;
  if (!data)   return null;

  if (!data.link.is_active)
    return <div className="quiz-error">This link is no longer active.</div>;
  if (data.link.expires_at && new Date(data.link.expires_at) < new Date())
    return <div className="quiz-error">This link has expired.</div>;
  if (!data.link.allow_response)
    return <div className="quiz-error">This link does not allow responses.</div>;

  return <QuizForm survey={data} token={token} />;
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
