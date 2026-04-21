import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { UITestPage } from "./pages/UITestPage";
import { NodePage } from "./pages/NodePage";
import { FormFillerPage } from "./pages/FormFillerPage";
import { ThemeProvider } from "./context/ThemeContext";
import "./App.css";

function AppRoutes() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Routes>
        <Route path="/ui-test" element={<UITestPage />} />
        <Route path="/node" element={<NodePage />} />
        <Route path="/node/preview" element={<FormFillerPage />} />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/node" replace />} />
    </Routes>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </ThemeProvider>
  );
}