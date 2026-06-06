import ReactMarkdown from "react-markdown";
import type { Message } from "@/lib/api";

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={[
          "max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
          isUser
            ? "bg-accent text-white rounded-br-sm"
            : "bg-white text-neutral-800 shadow-sm ring-1 ring-neutral-200 rounded-bl-sm",
        ].join(" ")}
      >
        <div className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}

export function TypingBubble() {
  return (
    <div className="flex justify-start">
      <div className="rounded-2xl rounded-bl-sm bg-white px-4 py-3 shadow-sm ring-1 ring-neutral-200">
        <span className="dot" />
        <span className="dot ml-1" />
        <span className="dot ml-1" />
      </div>
    </div>
  );
}
