"use client";

import { useEffect, useRef, useState } from "react";
import { sendChat, type Message } from "@/lib/api";
import { MessageBubble, TypingBubble } from "@/components/MessageBubble";
import { SuggestedQuestions } from "@/components/SuggestedQuestions";

const BOT_NAME = "Portfolio Agent";

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
    <main className="relative z-10 mx-auto flex h-[100dvh] max-w-2xl flex-col px-5">
      {/* Header */}
      <header className="flex animate-fade-up items-center gap-3.5 border-b border-white/[0.06] py-5">
        <div className="relative">
          <div className="absolute inset-0 rounded-xl bg-accent/30 blur-md" aria-hidden />
          <div className="relative flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-accent to-accent-deep font-display text-xl text-ink">
            BE
          </div>
        </div>
        <div className="flex-1">
          <h1 className="font-display text-[1.45rem] leading-none tracking-tight">{BOT_NAME}</h1>
          <p className="mt-1 font-mono text-[0.7rem] uppercase tracking-wider text-muted">
            Brahim Elkhattabi · AI Engineer
          </p>
        </div>
        <span className="flex items-center gap-1.5 rounded-full border border-white/10 bg-panel/60 px-2.5 py-1 font-mono text-[0.65rem] text-muted">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px] shadow-emerald-400/60" />
          online
        </span>
      </header>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 space-y-3.5 overflow-y-auto py-6">
        {empty && (
          <div className="mx-auto mt-6 max-w-md space-y-7">
            <div className="animate-fade-up space-y-3">
              <h2 className="font-display text-3xl leading-tight">
                Hi — I&apos;m Brahim&apos;s <span className="italic text-accent">portfolio agent</span>.
              </h2>
              <p className="text-sm leading-relaxed text-muted">
                I know his projects, AI engineering work, and skills inside out. Ask me anything — or
                start with one of these:
              </p>
            </div>
            <SuggestedQuestions onPick={ask} />
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
        className="sticky bottom-0 flex items-center gap-2 bg-gradient-to-t from-ink via-ink to-transparent pb-5 pt-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about Brahim…"
          maxLength={1000}
          className="flex-1 rounded-full border border-white/10 bg-panel px-5 py-3 text-sm text-cream placeholder:text-muted/70 outline-none transition focus:border-accent/60 focus:ring-4 focus:ring-accent/10"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          aria-label="Send"
          className="flex h-11 w-11 items-center justify-center rounded-full bg-accent text-ink transition hover:bg-accent-deep disabled:opacity-30"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12h14M13 6l6 6-6 6" />
          </svg>
        </button>
      </form>
    </main>
  );
}
