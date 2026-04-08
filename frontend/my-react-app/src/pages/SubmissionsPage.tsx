import { Fragment, useCallback, useState } from "react";
import { useParams } from "react-router-dom";
import { getSubmission, listSubmissions } from "../api/submissions";
import type {
  AnswerOut,
  CoreSubmissionOut,
  SubmissionChannel,
  SubmissionStatus,
} from "../api/types";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Select } from "../components/ui/Select";
import { Spinner } from "../components/ui/Spinner";
import { useFetch } from "../hooks/useFetch";
import "../App.css";
import "./SubmissionsPage.css";

const STATUS_BADGE: Record<SubmissionStatus, "warning" | "success" | "danger"> = {
  pending: "warning",
  stored: "success",
  failed: "danger",
};

const CHANNEL_BADGE: Record<SubmissionChannel, "muted" | "accent"> = {
  authenticated: "muted",
  public_link: "accent",
  system: "muted",
};

export function SubmissionsPage() {
  const { projectId, surveyId } = useParams<{
    projectId: string;
    surveyId?: string;
  }>();
  const pid = Number(projectId);
  const sid = surveyId ? Number(surveyId) : undefined;

  const [status, setStatus] = useState<"" | SubmissionStatus>("");
  const [channel, setChannel] = useState<"" | SubmissionChannel>("");
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [expandedAnswers, setExpandedAnswers] = useState<AnswerOut[] | null>(null);
  const [expandedLoading, setExpandedLoading] = useState(false);

  const fetcher = useCallback(
    () =>
      listSubmissions(pid, {
        survey_id: sid,
        status: status || undefined,
        submission_channel: (channel as SubmissionChannel) || undefined,
        page,
        page_size: pageSize,
      }),
    [pid, sid, status, channel, page],
  );
  const { data, loading, error, refetch } = useFetch(fetcher);

  async function toggleExpand(sub: CoreSubmissionOut) {
    if (expandedId === sub.id) {
      setExpandedId(null);
      setExpandedAnswers(null);
      return;
    }
    setExpandedId(sub.id);
    setExpandedAnswers(null);
    setExpandedLoading(true);
    try {
      const result = await getSubmission(pid, sub.id, true);
      setExpandedAnswers(result.answers);
    } finally {
      setExpandedLoading(false);
    }
  }

  function applyFilters() {
    setPage(1);
    refetch();
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">
          Submissions
          {sid && <span className="submissions-scope"> — Survey {sid}</span>}
        </h1>
      </div>

      {/* Filters */}
      <div className="submissions-filters">
        <Select
          label="Status"
          options={[
            { value: "", label: "All statuses" },
            { value: "pending", label: "Pending" },
            { value: "stored", label: "Stored" },
            { value: "failed", label: "Failed" },
          ]}
          value={status}
          onChange={(e) => setStatus(e.target.value as "" | SubmissionStatus)}
        />
        <Select
          label="Channel"
          options={[
            { value: "", label: "All channels" },
            { value: "authenticated", label: "Authenticated" },
            { value: "public_link", label: "Public link" },
            { value: "system", label: "System" },
          ]}
          value={channel}
          onChange={(e) => setChannel(e.target.value as "" | SubmissionChannel)}
        />
        <div className="submissions-filters__btn">
          <Button variant="secondary" onClick={applyFilters}>Apply</Button>
        </div>
      </div>

      {loading && <Spinner />}
      {error && <div className="error-banner">{error}</div>}

      {data && (
        <>
          {data.items.length === 0 ? (
            <div className="empty-state">No submissions found.</div>
          ) : (
            <div className="item-list">
              {data.items.map((sub) => (
                <Fragment key={sub.id}>
                  <div
                    className={`item-list__row submission-row ${expandedId === sub.id ? "submission-row--expanded" : ""}`}

                    onClick={() => toggleExpand(sub)}
                  >
                    <div className="item-list__main">
                      <div className="submission-row__top">
                        <span className="submission-id">#{sub.id}</span>
                        <Badge variant={STATUS_BADGE[sub.status]}>{sub.status}</Badge>
                        <Badge variant={CHANNEL_BADGE[sub.submission_channel]}>
                          {sub.submission_channel.replace("_", " ")}
                        </Badge>
                        {sub.is_anonymous && <Badge variant="muted">anon</Badge>}
                      </div>
                      <div className="submission-row__meta">
                        {sub.submitted_at
                          ? new Date(sub.submitted_at).toLocaleString()
                          : "—"}
                        {sub.survey_id && (
                          <span className="submission-survey">Survey {sub.survey_id}</span>
                        )}
                      </div>
                    </div>
                    <span className="submission-expand-icon">
                      {expandedId === sub.id ? "▲" : "▼"}
                    </span>
                  </div>
                  {expandedId === sub.id && (
                    <div key={`${sub.id}-answers`} className="submission-answers">
                      {expandedLoading ? (
                        <Spinner size={16} />
                      ) : expandedAnswers && expandedAnswers.length > 0 ? (
                        expandedAnswers.map((a) => (
                          <div key={a.id} className="submission-answer">
                            <code className="answer-key">{a.question_key}</code>
                            <span className="answer-value">
                              {JSON.stringify(a.answer_value)}
                            </span>
                            <Badge variant="muted">{a.answer_family}</Badge>
                          </div>
                        ))
                      ) : (
                        <span className="submission-no-answers">No answers recorded.</span>
                      )}
                    </div>
                  )}
                </Fragment>
              ))}
            </div>
          )}

          {/* Pagination */}
          <div className="pagination">
            <Button
              size="sm"
              variant="secondary"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              ← Prev
            </Button>
            <span>
              Page {data.page} of {Math.max(1, Math.ceil(data.total / pageSize))}
            </span>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => setPage((p) => p + 1)}
              disabled={page * pageSize >= data.total}
            >
              Next →
            </Button>
            <span className="pagination__total">{data.total} total</span>
          </div>
        </>
      )}
    </div>
  );
}
