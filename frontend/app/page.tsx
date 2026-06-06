"use client";

import { useEffect, useRef, useState } from "react";
import { sendChat, type Message } from "@/lib/api";
import { MessageBubble, TypingBubble } from "@/components/MessageBubble";
import { SuggestedQuestions } from "@/components/SuggestedQuestions";

const BOT_NAME = "Brahim's AI"; // change to taste

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  async function ask(question: string) {
    const q = question.trim();
    if (!q || loading) return;
    const history = messages;
    setMessages((m) => [...m, { role: "user", content: q }]);
    setInput("");
    setLoading(true);
    try {
      const reply = await sendChat(q, history);
      setMessages((m) => [...m, { role: "assistant", content: reply }]);
    } catch {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: "Something went wrong — please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const empty = messages.length === 0;

  return (
    <main className="mx-auto flex h-screen max-w-2xl flex-col px-4">
      {/* Header */}
      <header className="flex items-center gap-3 py-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent text-lg font-semibold text-white">
          B
        </div>
        <div>
          <h1 className="text-base font-semibold">{BOT_NAME}</h1>
          <p className="text-xs text-neutral-500">Ask me about Brahim's work, projects & skills</p>
        </div>
      </header>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto pb-4">
        {empty && (
          <div className="mt-10 space-y-5 text-center">
            <p className="text-lg font-medium text-neutral-700">
              👋 Hi! I'm {BOT_NAME}. I can tell you all about Brahim.
            </p>
            <p className="text-sm text-neutral-500">Try one of these:</p>
            <div className="flex justify-center">
              <SuggestedQuestions onPick={ask} />
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}
        {loading && <TypingBubble />}
      </div>

      {/* Composer */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(input);
        }}
        className="sticky bottom-0 flex items-center gap-2 bg-neutral-50 py-4"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about Brahim…"
          maxLength={1000}
          className="flex-1 rounded-full border border-neutral-300 bg-white px-4 py-2.5 text-sm outline-none focus:border-accent focus:ring-1 focus:ring-accent"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-white transition disabled:opacity-40"
        >
          Send
        </button>
      </form>
    </main>
  );
}
