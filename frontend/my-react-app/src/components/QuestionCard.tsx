import { useRef, useState } from "react";
import "./QuestionCard.css";

export type Question = {
  id: number;
  title: string;
  logic: {
    condition: string;
    action: string;
  } | null;
};

type Option = {
  id: number;
  text: string;
};

type Props = {
  question: Question;
  index: number; // card number, e.g. 1 → "Q1"
  onEdit: (id: number) => void;
  onDelete: (id: number) => void;
  onEditLogic: (id: number) => void;
};

function optionLabel(questionIndex: number, optionIndex: number): string {
  const letter = String.fromCharCode(65 + optionIndex); // A, B, C…
  return `${questionIndex}${letter}`;
}

export function QuestionCard({ question, index, onDelete }: Props) {
  const [title, setTitle] = useState(question.title);
  const [editingTitle, setEditingTitle] = useState(false);
  const [options, setOptions] = useState<Option[]>([]);
  const [activeOption, setActiveOption] = useState<number | null>(null);
  const nextId = useRef(1);

  function addOption() {
    const id = nextId.current++;
    setOptions(prev => [...prev, { id, text: "" }]);
    setActiveOption(id);
  }

  function updateOption(id: number, text: string) {
    setOptions(prev => prev.map(o => o.id === id ? { ...o, text } : o));
  }

  function removeOption(id: number) {
    setOptions(prev => prev.filter(o => o.id !== id));
    if (activeOption === id) setActiveOption(null);
  }

  return (
    <div className="qcard">

      {/* ── Header row ───────────────────────────── */}
      <div className="qcard__header">
        <span className="qcard__index">Q{index}</span>
        <div className="qcard__header-actions">
          <button className="qcard__icon-btn" title="Settings" aria-label="Settings">
            <SettingsIcon />
          </button>
          <button
            className="qcard__icon-btn qcard__icon-btn--danger"
            title="Delete question"
            aria-label="Delete"
            onClick={() => onDelete(question.id)}
          >
            <TrashIcon />
          </button>
        </div>
      </div>

      {/* ── Question title ───────────────────────── */}
      <div className="qcard__question-area">
        {editingTitle ? (
          <textarea
            className="qcard__title-input"
            value={title}
            rows={2}
            onChange={e => setTitle(e.target.value)}
            onBlur={() => setEditingTitle(false)}
            onKeyDown={e => {
              if (e.key === "Escape") setEditingTitle(false);
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                setEditingTitle(false);
              }
            }}
            autoFocus
            placeholder="Type your question…"
          />
        ) : (
          <div
            className="qcard__title"
            onClick={() => setEditingTitle(true)}
            title="Click to edit"
          >
            {title || <span className="qcard__title-placeholder">Type your question…</span>}
          </div>
        )}
      </div>

      {/* ── Answer options ───────────────────────── */}
      <div className="qcard__options">
        {options.map((opt, i) => {
          const label = optionLabel(index, i);
          const isActive = activeOption === opt.id;

          return (
            <div
              key={opt.id}
              className={`qcard__option ${isActive ? "qcard__option--active" : ""}`}
              onClick={() => !isActive && setActiveOption(opt.id)}
            >
              <span className="qcard__option-label">{label}</span>

              {isActive ? (
                <input
                  className="qcard__option-input"
                  type="text"
                  value={opt.text}
                  autoFocus
                  placeholder="Enter answer…"
                  onChange={e => updateOption(opt.id, e.target.value)}
                  onBlur={() => setActiveOption(null)}
                  onKeyDown={e => {
                    if (e.key === "Enter") {
                      setActiveOption(null);
                      addOption();
                    }
                    if (e.key === "Escape") setActiveOption(null);
                  }}
                />
              ) : (
                <span className="qcard__option-text">
                  {opt.text || <span className="qcard__option-placeholder">Empty option</span>}
                </span>
              )}

              <button
                className="qcard__option-remove"
                onClick={e => { e.stopPropagation(); removeOption(opt.id); }}
                aria-label="Remove option"
                tabIndex={-1}
              >
                ×
              </button>
            </div>
          );
        })}

        <button className="qcard__add-option" onClick={addOption}>
          <span className="qcard__add-option-icon">+</span>
          <span>Add option</span>
        </button>
      </div>
    </div>
  );
}

/* ── Inline SVG icons ─────────────────────────── */

function SettingsIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="8" cy="8" r="2.5" stroke="currentColor" strokeWidth="1.4"/>
      <path
        d="M8 1v1.5M8 13.5V15M1 8h1.5M13.5 8H15M2.93 2.93l1.06 1.06M12.01 12.01l1.06 1.06M13.07 2.93l-1.06 1.06M3.99 12.01l-1.06 1.06"
        stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"
      />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M2 4h12M5 4V2.5A.5.5 0 0 1 5.5 2h5a.5.5 0 0 1 .5.5V4M6 7v5M10 7v5M3 4l1 9.5A.5.5 0 0 0 4.5 14h7a.5.5 0 0 0 .497-.45L13 4"
        stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"
      />
    </svg>
  );
}
