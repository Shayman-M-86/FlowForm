import { BrowserRouter, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { PublicShell } from "./components/layout/PublicShell";
import { HomePage } from "./pages/HomePage";
import { SurveysPage } from "./pages/SurveysPage";
import { SurveyEditorPage } from "./pages/SurveyEditorPage";
import { SubmissionsPage } from "./pages/SubmissionsPage";
import { TakeSurveyPage } from "./pages/TakeSurveyPage";
import { QuizTakerPage } from "./pages/QuizTakerPage";
import { PublicSurveyBrowsePage } from "./pages/PublicSurveyBrowsePage";
import { ProtectedApp } from "./components/auth/ProtectedApp";
import { BuilderPage } from "./pages/Builder";
import { NodePage } from "./pages/NodePage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { UITestPage } from "./pages/UITestPage";
import { useAppMode } from "./hooks/useAppMode";
import "./App.css";

// Inner component so useNavigate is inside BrowserRouter
function AppRoutes() {
  const navigate = useNavigate();
  const [mode, setMode] = useAppMode();

  function handleModeSwitch(next: typeof mode) {
    setMode(next);
    if (next === "explore") {
      navigate("/explore");
    } else {
      navigate("/");
    }
  }

  return (
    <Routes>
      {/* Bare quiz routes — no shell, no auth */}
      <Route path="/quiz/:publicSlug" element={<QuizTakerPage mode="slug" />} />
      <Route path="/quiz/resolve" element={<QuizTakerPage mode="token" />} />
      <Route path="/builder" element={<BuilderPage />} />
      <Route path="/ui-test" element={<UITestPage />} />

      {/* Explore mode — public shell, no auth required */}
      <Route
        element={<PublicShell mode={mode} onModeSwitch={handleModeSwitch} />}
      >
        <Route path="/explore" element={<PublicSurveyBrowsePage />} />
        <Route path="/explore/take" element={<TakeSurveyPage />} />
      </Route>

      {/* Manage mode — protected shell, auth required */}
      <Route
        element={
          <ProtectedApp>
            <AppShell mode={mode} onModeSwitch={handleModeSwitch} />
          </ProtectedApp>
        }
      >
        <Route path="/" element={<HomePage />} />
        <Route path="/node" element={<NodePage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/take" element={<TakeSurveyPage />} />
        <Route path="/projects/:projectRef/surveys" element={<SurveysPage />} />
        <Route path="/projects/:projectRef/surveys/:surveyId" element={<SurveyEditorPage />} />
        <Route path="/projects/:projectRef/surveys/:surveyId/submissions" element={<SubmissionsPage />} />
        <Route path="/projects/:projectRef/submissions" element={<SubmissionsPage />} />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}
