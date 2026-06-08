import ReactMarkdown from "react-markdown";
import type { Message } from "@/lib/api";

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex animate-fade-up ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={[
          "max-w-[86%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
          isUser
            ? "rounded-br-md bg-accent font-medium text-ink"
            : "rounded-bl-md border border-white/10 bg-surface text-cream shadow-[0_1px_0_rgba(255,255,255,0.04)_inset]",
        ].join(" ")}
      >
        {isUser ? (
          message.content
        ) : (
          <div className="answer-prose">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}

export function TypingBubble() {
  return (
    <div className="flex animate-fade-in justify-start">
      <div className="flex items-center gap-1 rounded-2xl rounded-bl-md border border-white/10 bg-surface px-4 py-3.5">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </div>
    </div>
  );
}
