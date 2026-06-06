// Edit these to the questions you most want recruiters to ask.
export const SUGGESTED = [
  "What has Brahim built?",
  "What's his experience with LLMs?",
  "What's his tech stack?",
  "What kind of role is he looking for?",
];

export function SuggestedQuestions({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {SUGGESTED.map((q) => (
        <button
          key={q}
          onClick={() => onPick(q)}
          className="rounded-full border border-neutral-300 bg-white px-3 py-1.5 text-xs text-neutral-700 transition hover:border-accent hover:text-accent"
        >
          {q}
        </button>
      ))}
    </div>
  );
}
