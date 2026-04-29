import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listPublicSurveys } from "../api/public";
import type { SurveyOut } from "../api/types";
import { Button, Spinner } from "../index.optimized";
import { useFetch } from "../hooks/useFetch";
import "./PublicSurveyBrowsePage.css";

const PAGE_SIZE = 20;

function SurveyCard({ survey }: { survey: SurveyOut }) {
  const navigate = useNavigate();
  const canTake = survey.public_slug && survey.published_version_id != null;

  return (
    <div className="browse-card">
      <div className="browse-card__body">
        <h3 className="browse-card__title">{survey.title}</h3>
        {survey.public_slug && (
          <span className="browse-card__slug">/{survey.public_slug}</span>
        )}
      </div>
      <div className="browse-card__action">
        {canTake ? (
          <Button
            variant="primary"
            onClick={() => navigate(`/quiz/${encodeURIComponent(survey.public_slug!)}`)}
          >
            Take survey
          </Button>
        ) : (
          <span className="browse-card__unavailable">Not accepting responses</span>
        )}
      </div>
    </div>
  );
}

export function PublicSurveyBrowsePage() {
  const [page, setPage] = useState(1);

  const fetcher = useCallback(
    () => listPublicSurveys(page, PAGE_SIZE),
    [page],
  );
  const { data, loading, error } = useFetch(fetcher, [page]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="browse-page">
      <div className="browse-header">
        <h1 className="browse-title">Browse Surveys</h1>
        <p className="browse-subtitle">Publicly available surveys you can fill out.</p>
      </div>

      {loading && (
        <div className="browse-loading">
          <Spinner />
        </div>
      )}

      {error && <div className="browse-error">{error}</div>}

      {!loading && !error && data && (
        <>
          {data.items.length === 0 ? (
            <div className="browse-empty">No public surveys available yet.</div>
          ) : (
            <div className="browse-list">
              {data.items.map((s) => (
                <SurveyCard key={s.id} survey={s} />
              ))}
            </div>
          )}

          {data.total > PAGE_SIZE && (
            <div className="browse-pagination">
              <Button
                variant="ghost"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <span className="browse-pagination__info">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="ghost"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
