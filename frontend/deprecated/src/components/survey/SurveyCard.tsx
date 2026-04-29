import { useNavigate } from "react-router-dom";
import { Badge } from "../../index.optimized";
import type { SurveyOut } from "../../api/types";
import "./SurveyCard.css";

interface SurveyCardProps {
  survey: SurveyOut;
  projectRef: string;
}

const VISIBILITY_BADGE: Record<string, "muted" | "accent" | "success"> = {
  private: "muted",
  link_only: "accent",
  public: "success",
};

export function SurveyCard({ survey, projectRef }: SurveyCardProps) {
  const navigate = useNavigate();

  return (
    <button
      className="survey-card"
      onClick={() => navigate(`/projects/${projectRef}/surveys/${survey.id}`)}
    >
      <div className="survey-card__top">
        <span className="survey-card__title">{survey.title}</span>
        <Badge variant={VISIBILITY_BADGE[survey.visibility] ?? "muted"}>
          {survey.visibility.replace("_", " ")}
        </Badge>
      </div>
      <div className="survey-card__meta">
        {survey.published_version_id ? (
          <Badge variant="success">published</Badge>
        ) : (
          <Badge variant="muted">unpublished</Badge>
        )}
        <span className="survey-card__date">
          Updated {new Date(survey.updated_at).toLocaleDateString()}
        </span>
      </div>
    </button>
  );
}
