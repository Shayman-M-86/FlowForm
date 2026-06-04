import { useState, type ReactNode } from "react";

export interface SurveyDebugCard {
  title: string;
  subtitle?: ReactNode;
  data: unknown;
}

interface SurveyDebugCardsProps {
  cards: SurveyDebugCard[];
}

export function SurveyDebugCards({ cards }: SurveyDebugCardsProps) {
  const [collapsedCards, setCollapsedCards] = useState<Set<string>>(() => new Set());

  function toggleCard(title: string) {
    setCollapsedCards((current) => {
      const next = new Set(current);
      if (next.has(title)) {
        next.delete(title);
      } else {
        next.add(title);
      }
      return next;
    });
  }

  return (
    <aside className="fixed bottom-4 right-4 z-50 flex max-h-[calc(100vh-32px)] w-[420px] flex-col gap-3 overflow-y-auto font-mono text-[0.78rem] text-[var(--debug-text)]">
      {cards.map((card) => {
        const collapsed = collapsedCards.has(card.title);
        return (
          <section
            key={card.title}
            className="flex min-h-0 w-[420px] shrink-0 flex-col overflow-hidden rounded-xl border border-border bg-[var(--debug-bg)] shadow"
          >
            <header className="flex items-center justify-between gap-3 border-b border-[var(--debug-border)] px-3 py-2 text-[0.72rem] font-semibold uppercase tracking-[0.04em]">
              <button
                type="button"
                className="min-w-0 flex-1 truncate text-left uppercase tracking-[0.04em]"
                aria-expanded={!collapsed}
                onClick={() => toggleCard(card.title)}
              >
                {card.title}
              </button>
              {card.subtitle && (
                <span className="shrink-0 font-medium text-[var(--debug-text-dim)]">
                  {card.subtitle}
                </span>
              )}
              <button
                type="button"
                className="flex size-6 shrink-0 items-center justify-center rounded-md border border-[var(--debug-border)] text-[var(--debug-text-dim)]"
                aria-label={`${collapsed ? "Expand" : "Collapse"} ${card.title}`}
                aria-expanded={!collapsed}
                onClick={() => toggleCard(card.title)}
              >
                {collapsed ? "+" : "-"}
              </button>
            </header>
            {!collapsed && (
              <pre className="m-0 min-h-0 max-h-[32vh] overflow-auto whitespace-pre p-3 leading-[1.45]">
                {JSON.stringify(card.data, null, 2)}
              </pre>
            )}
          </section>
        );
      })}
    </aside>
  );
}
