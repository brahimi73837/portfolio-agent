// Tiny client-side helper for talking to our own /api/chat proxy route.

export type Role = "user" | "assistant";
export interface Message {
  role: Role;
  content: string;
}

export async function sendChat(message: string, history: Message[]): Promise<string> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });
  if (!res.ok) {
    throw new Error(`Request failed (${res.status})`);
  }
  const data = await res.json();
  return data.reply as string;
}
