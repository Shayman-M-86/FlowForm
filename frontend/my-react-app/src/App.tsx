import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { HomePage } from "./pages/HomePage";
import { SurveysPage } from "./pages/SurveysPage";
import { SurveyEditorPage } from "./pages/SurveyEditorPage";
import { SubmissionsPage } from "./pages/SubmissionsPage";
import { TakeSurveyPage } from "./pages/TakeSurveyPage";
import { QuizTakerPage } from "./pages/QuizTakerPage";
import { ProtectedApp } from "./components/auth/ProtectedApp";
import { BuilderPage } from "./pages/Builder";
import { ProjectsPage } from "./pages/ProjectsPage";
import "./App.css";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/quiz/:publicSlug" element={<QuizTakerPage mode="slug" />} />
        <Route path="/quiz/resolve" element={<QuizTakerPage mode="token" />} />
        <Route path="/builder" element={<BuilderPage />} />
        {/* Protected app routes */}
        <Route
          element={
            <ProtectedApp>
              <AppShell />
            </ProtectedApp>
          }
        >
          <Route path="/" element={<HomePage />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/take" element={<TakeSurveyPage />} />
          <Route path="/projects/:projectId/surveys" element={<SurveysPage />} />
          <Route path="/projects/:projectId/surveys/:surveyId" element={<SurveyEditorPage />} />
          <Route path="/projects/:projectId/surveys/:surveyId/submissions" element={<SubmissionsPage />} />
          <Route path="/projects/:projectId/submissions" element={<SubmissionsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}