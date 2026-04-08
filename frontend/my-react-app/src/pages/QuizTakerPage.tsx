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

// ── Individual question renderers ─────────────────────────────────────────────

interface QuestionRendererProps {
  schema: Record<string, unknown>;
  questionKey: string;
  value: unknown;
  onChange: (value: unknown) => void;
}

function QuestionRenderer({ schema, questionKey, value, onChange }: QuestionRendererProps) {
  const type = schema.type as string;
  const label = (schema.label as string) ?? questionKey;
  const required = Boolean(schema.required);

  return (
    <div className="quiz-question">
      <div className="quiz-question__label">
        {label}
        {required && <span className="quiz-required">*</span>}
      </div>

      {type === "choice" && (
        <div className="quiz-choices">
          {((schema.options as string[]) ?? []).map((opt) => (
            <label key={opt} className="quiz-choice">
              <input
                type="radio"
                name={questionKey}
                value={opt}
                checked={value === opt}
                onChange={() => onChange(opt)}
              />
              <span>{opt}</span>
            </label>
          ))}
        </div>
      )}

      {type === "field" && (
        <input
          className="quiz-field-input"
          type={(schema.field_type as string) ?? "text"}
          value={(value as string) ?? ""}
          required={required}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Your answer"
        />
      )}

      {type === "rating" && (
        <div className="quiz-rating">
          {Array.from({ length: (schema.max as number) ?? 5 }, (_, i) => i + 1).map((n) => (
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
      )}

      {type === "matching" && (
        <div className="quiz-matching">
          {((schema.pairs as { left: string; right: string }[]) ?? []).map((pair, i) => {
            const answers = (value as Record<string, string>) ?? {};
            return (
              <div key={i} className="quiz-matching__row">
                <span className="quiz-matching__left">{pair.left}</span>
                <span className="quiz-matching__arrow">→</span>
                <select
                  className="quiz-matching__select"
                  value={answers[pair.left] ?? ""}
                  onChange={(e) =>
                    onChange({ ...answers, [pair.left]: e.target.value })
                  }
                >
                  <option value="">Select…</option>
                  {((schema.pairs as { left: string; right: string }[]) ?? []).map(
                    (p) => (
                      <option key={p.right} value={p.right}>{p.right}</option>
                    ),
                  )}
                </select>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Quiz form (given resolved survey + optional token) ────────────────────────

interface QuizFormProps {
  survey: PublicSurveyOut | ResolveLinkOut;
  token?: string;
}

function QuizForm({ survey, token }: QuizFormProps) {
  const surveyData = "survey" in survey ? survey.survey : null;
  const version =
    "published_version" in survey ? survey.published_version : null;

  const questions =
    version?.compiled_schema?.questions ?? [];

  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  function setAnswer(key: string, value: unknown) {
    setAnswers((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!version || !token) return;
    setSubmitting(true);
    setSubmitError(null);

    const answerList: AnswerIn[] = questions.map((q) => {
      const val = answers[q.question_key];
      const type = (q.question_schema.type as string) ?? "field";
      let family = "text";
      if (type === "choice") family = "choice";
      else if (type === "rating") family = "number";
      else if (type === "matching") family = "matching";
      else {
        const ft = (q.question_schema.field_type as string) ?? "text";
        family = ft === "number" ? "number" : "text";
      }
      return {
        question_key: q.question_key,
        answer_family: family,
        answer_value: { value: val },
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
    return (
      <div className="quiz-error">
        This survey has no published version yet.
      </div>
    );
  }

  return (
    <form className="quiz-form" onSubmit={handleSubmit}>
      <h1 className="quiz-title">{surveyData?.title ?? "Quiz"}</h1>
      {questions.length === 0 ? (
        <p className="quiz-no-questions">No questions in this quiz.</p>
      ) : (
        questions.map((q) => (
          <QuestionRenderer
            key={q.question_key}
            schema={q.question_schema}
            questionKey={q.question_key}
            value={answers[q.question_key]}
            onChange={(v) => setAnswer(q.question_key, v)}
          />
        ))
      )}

      {submitError && (
        <div style={{ color: "var(--danger)", fontSize: 13 }}>{submitError}</div>
      )}

      {token ? (
        <Button
          type="submit"
          variant="primary"
          disabled={submitting}
        >
          {submitting ? "Submitting…" : "Submit"}
        </Button>
      ) : (
        <p style={{ fontSize: 13, color: "var(--muted)" }}>
          Preview mode — submission requires a public link token.
        </p>
      )}
    </form>
  );
}

// ── Page: slug mode ───────────────────────────────────────────────────────────

function SlugQuizPage({ slug }: { slug: string }) {
  const fetcher = useCallback(() => getPublicSurvey(slug), [slug]);
  const { data, loading, error } = useFetch(fetcher);

  if (loading) return <div className="quiz-loading"><Spinner /></div>;
  if (error) return <div className="quiz-error">{error}</div>;
  if (!data) return null;

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
  const { data, loading, error } = useFetch(token ? fetcher : null);

  if (!token) return <div className="quiz-error">No token provided in URL (?token=…).</div>;
  if (loading) return <div className="quiz-loading"><Spinner /></div>;
  if (error) return <div className="quiz-error">{error}</div>;
  if (!data) return null;

  if (!data.link.is_active) {
    return <div className="quiz-error">This link is no longer active.</div>;
  }
  if (data.link.expires_at && new Date(data.link.expires_at) < new Date()) {
    return <div className="quiz-error">This link has expired.</div>;
  }
  if (!data.link.allow_response) {
    return <div className="quiz-error">This link does not allow responses.</div>;
  }

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
