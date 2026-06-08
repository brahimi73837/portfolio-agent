// The 4 strongest "getting to know Brahim" questions — each maps to rich answers
// in the knowledge base. "Who is Brahim?" leads.
export const SUGGESTED = [
  "Who is Brahim?",
  "What's his experience with AI & LLMs?",
  "What are his standout projects?",
  "What kind of role is he looking for?",
];

export function SuggestedQuestions({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="flex flex-col gap-2">
      {SUGGESTED.map((q, i) => (
        <button
          key={q}
          onClick={() => onPick(q)}
          style={{ animationDelay: `${0.25 + i * 0.07}s` }}
          className="group flex animate-fade-up items-center gap-2.5 rounded-xl border border-white/10 bg-panel/60 px-4 py-3 text-left text-sm text-cream/80 backdrop-blur transition hover:-translate-y-0.5 hover:border-accent/50 hover:bg-panel hover:text-cream"
        >
          <span className="font-mono text-xs text-accent transition group-hover:translate-x-0.5">
            &rsaquo;
          </span>
          {q}
        </button>
      ))}
    </div>
  );
}
