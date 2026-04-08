import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { getStoredProjectId } from "./components/layout/ProjectSelector";
import { SurveysPage } from "./pages/SurveysPage";
import { SurveyEditorPage } from "./pages/SurveyEditorPage";
import { SubmissionsPage } from "./pages/SubmissionsPage";
import { QuizTakerPage } from "./pages/QuizTakerPage";
import { ProtectedApp } from "./components/auth/ProtectedApp";
import "./App.css";

function DefaultRedirect() {
  const id = getStoredProjectId();

  return id ? (
    <Navigate to={`/projects/${id}/surveys`} replace />
  ) : (
    <Navigate to="/projects/1/surveys" replace />
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/quiz/:publicSlug" element={<QuizTakerPage mode="slug" />} />
        <Route path="/quiz/resolve" element={<QuizTakerPage mode="token" />} />

        {/* Protected app routes */}
        <Route
          element={
            <ProtectedApp>
              <AppShell />
            </ProtectedApp>
          }
        >
          <Route path="/" element={<DefaultRedirect />} />
          <Route path="/projects/:projectId/surveys" element={<SurveysPage />} />
          <Route path="/projects/:projectId/surveys/:surveyId" element={<SurveyEditorPage />} />
          <Route path="/projects/:projectId/surveys/:surveyId/submissions" element={<SubmissionsPage />} />
          <Route path="/projects/:projectId/submissions" element={<SubmissionsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}