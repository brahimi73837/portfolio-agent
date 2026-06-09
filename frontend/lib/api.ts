// Client-side helper for talking to our own /api/chat proxy route.

export type Role = "user" | "assistant";
export interface Message {
  role: Role;
  content: string;
}

export type ErrorCode = "rate_limit" | "timeout" | "network" | "server" | "unknown";

// Carries a coarse error category so the UI can show a specific, reassuring message.
export class ChatError extends Error {
  code: ErrorCode;
  constructor(code: ErrorCode) {
    super(code);
    this.code = code;
  }
}

export async function sendChat(message: string, history: Message[]): Promise<string> {
  let res: Response;
  try {
    res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history }),
    });
  } catch {
    // fetch only rejects on a genuine network/connection failure.
    throw new ChatError("network");
  }

  if (!res.ok) {
    if (res.status === 429) throw new ChatError("rate_limit");
    if (res.status === 408 || res.status === 504) throw new ChatError("timeout");
    if (res.status >= 500) throw new ChatError("server");
    throw new ChatError("unknown");
  }

  const data = await res.json();
  return data.reply as string;
}
