import { useCallback, useState } from "react";
import { useApi } from "../../api/useApi";
import type { QuestionOut } from "../../api/types";
import { useFetch } from "../../hooks/useFetch";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Spinner } from "../ui/Spinner";
import { QuestionEditor } from "./QuestionEditor";
import "../../App.css";
import "./QuestionList.css";

interface QuestionListProps {
  projectId: number;
  surveyId: number;
  versionId: number;
  readOnly?: boolean;
}

export function QuestionList({ projectId, surveyId, versionId, readOnly }: QuestionListProps) {
  const api = useApi();
  const fetcher = useCallback(
    () => api.listQuestions(projectId, surveyId, versionId),
    [api, projectId, surveyId, versionId],
  );
  const { data: questions, loading, error, refetch } = useFetch(fetcher);

  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<QuestionOut | null>(null);

  function openAdd() { setEditing(null); setEditorOpen(true); }
  function openEdit(q: QuestionOut) { setEditing(q); setEditorOpen(true); }

  async function handleSave(data: Parameters<typeof api.createQuestion>[3]) {
    if (editing) {
      await api.updateQuestion(projectId, surveyId, versionId, editing.id, data);
    } else {
      await api.createQuestion(projectId, surveyId, versionId, data);
    }
    refetch(); // only reached if the API call succeeded
  }

  async function handleDelete(q: QuestionOut) {
    if (!confirm(`Delete question "${q.question_key}"?`)) return;
    await api.deleteQuestion(projectId, surveyId, versionId, q.id);
    refetch();
  }

  if (loading) return <Spinner />;
  if (error) return <div className="error-banner">{error}</div>;

  return (
    <div>
      {questions?.length === 0 ? (
        <div className="empty-state">No questions yet.</div>
      ) : (
        <div className="item-list">
          {questions?.map((q) => (
            <div key={q.id} className="item-list__row">
              <div className="item-list__main">
                <code className="question-key">{q.question_key}</code>
                <span className="question-label">
                  {(q.question_schema.label as string) ?? "—"}
                </span>
              </div>
              <Badge variant="accent">
                {(q.question_schema.type as string) ?? "?"}
              </Badge>
              {!readOnly && (
                <div className="item-list__actions">
                  <Button size="sm" variant="ghost" onClick={() => openEdit(q)}>Edit</Button>
                  <Button size="sm" variant="danger" onClick={() => handleDelete(q)}>Delete</Button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {!readOnly && (
        <div className="question-list__add">
          <Button variant="secondary" onClick={openAdd}>+ Add Question</Button>
        </div>
      )}

      <QuestionEditor
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        onSave={handleSave}
        initial={editing ?? undefined}
      />
    </div>
  );
}
