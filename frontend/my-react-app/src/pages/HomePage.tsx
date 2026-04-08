import { useNavigate } from "react-router-dom";
import { getStoredProjectId } from "../components/layout/ProjectSelector";
import "./HomePage.css";

export function HomePage() {
  const navigate = useNavigate();
  const projectId = getStoredProjectId() ?? 1;

  return (
    <div className="home-page">
      <div className="home-hero">
        <h1 className="home-hero__title">FlowForm</h1>
        <p className="home-hero__subtitle">
          Build surveys and quizzes, share them via public or private links,
          and review responses — all in one place.
        </p>
      </div>

      <div className="home-cards">
        <button
          className="home-card"
          onClick={() => navigate(`/projects/${projectId}/surveys`)}
        >
          <div className="home-card__icon">📋</div>
          <div className="home-card__body">
            <h2 className="home-card__title">Build</h2>
            <p className="home-card__desc">
              Create and manage surveys. Add questions, set rules, publish
              versions, and generate shareable links.
            </p>
          </div>
          <span className="home-card__arrow">→</span>
        </button>

        <button
          className="home-card"
          onClick={() => navigate("/take")}
        >
          <div className="home-card__icon">✏️</div>
          <div className="home-card__body">
            <h2 className="home-card__title">Take</h2>
            <p className="home-card__desc">
              Fill out a survey using a public link token or a direct public
              URL. Responses are recorded immediately.
            </p>
          </div>
          <span className="home-card__arrow">→</span>
        </button>
      </div>
    </div>
  );
}
