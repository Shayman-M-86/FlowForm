import { Select } from "../ui/Select";
import type { MatchingContent } from "../node/questionTypes";
import "../node/MatchingQuestion.css";

interface MatchingFormFillerProps {
  question: MatchingContent;
  value: Record<string, string>;
  onChange: (nextValue: Record<string, string>) => void;
}

export function MatchingFormFiller({
  question,
  value,
  onChange,
}: MatchingFormFillerProps) {
  const selectedMatchIds = new Set(Object.values(value).filter(Boolean));
  const selectOptions = [
    { value: "", label: "Select a match" },
    ...question.definition.matches.map((match) => ({
      value: match.id,
      label: match.label || match.id,
    })),
  ];

  function handleMatchChange(promptId: string, matchId: string) {
    onChange({
      ...value,
      [promptId]: matchId,
    });
  }

  return (
    <div className="form-filler-question__body">
      <div className="node-pill__matching-grid form-filler-matching__layout">
        <section className="node-pill__match-column">
          <div className="node-pill__match-column-head">
            <span className="node-pill__match-column-label">Prompts</span>
            <span className="node-pill__match-column-count">{question.definition.prompts.length}</span>
          </div>

          <div className="form-filler-matching__assignments">
            {question.definition.prompts.map((prompt) => (
              <div key={prompt.id} className="form-filler-matching__assignment">
                <div className="form-filler-matching__prompt-card">{prompt.label || prompt.id}</div>
                <Select
                  className="form-filler-matching__select"
                  label="Match"
                  value={value[prompt.id] ?? ""}
                  options={selectOptions}
                  onChange={(event) => handleMatchChange(prompt.id, event.target.value)}
                />
              </div>
            ))}
          </div>
        </section>

        <section className="node-pill__match-column">
          <div className="node-pill__match-column-head">
            <span className="node-pill__match-column-label">Available matches</span>
            <span className="node-pill__match-column-count">{question.definition.matches.length}</span>
          </div>

          <div className="node-pill__options">
            {question.definition.matches.map((match) => {
              const isSelected = selectedMatchIds.has(match.id);

              return (
                <div key={match.id} className="node-pill__option-row">
                  <div className={`form-filler-matching__match-card ${isSelected ? "form-filler-matching__match-card--selected" : ""}`}>
                    {match.label || match.id}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
}
