import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Input } from "../index.optimized";
import "../App.css";
import "./TakeSurveyPage.css";

export function TakeSurveyPage() {
  const navigate = useNavigate();
  const [token, setToken] = useState("");
  const [slug, setSlug] = useState("");

  function handleToken(e: React.FormEvent) {
    e.preventDefault();
    const t = token.trim();
    if (t) navigate(`/quiz/resolve?token=${encodeURIComponent(t)}`);
  }

  function handleSlug(e: React.FormEvent) {
    e.preventDefault();
    const s = slug.trim();
    if (s) navigate(`/quiz/${encodeURIComponent(s)}`);
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Take a Survey</h1>
      </div>

      <div className="take-sections">
        <div className="card take-section">
          <h2 className="take-section__title">Private link token</h2>
          <p className="take-section__desc">
            You received a one-time token from a survey creator. Paste it below
            to open the survey.
          </p>
          <form className="take-section__form" onSubmit={handleToken}>
            <Input
              label="Token"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Paste your token here"
            />
            <Button type="submit" variant="primary" disabled={!token.trim()}>
              Open survey
            </Button>
          </form>
        </div>

        <div className="card take-section">
          <h2 className="take-section__title">Public survey slug</h2>
          <p className="take-section__desc">
            Some surveys are publicly accessible by a short name. Enter the
            slug to open it directly.
          </p>
          <form className="take-section__form" onSubmit={handleSlug}>
            <Input
              label="Slug"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              placeholder="e.g. my-quiz"
            />
            <Button type="submit" variant="primary" disabled={!slug.trim()}>
              Open survey
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
