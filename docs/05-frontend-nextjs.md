# 05 — Frontend (Next.js)

A deliberately minimalist single-page chat. The whole point is: load fast, look clean, get out of the way.

## Files

| File | Job |
|---|---|
| [`app/page.tsx`](../frontend/app/page.tsx) | The chat screen (state, send loop, render) |
| [`app/api/chat/route.ts`](../frontend/app/api/chat/route.ts) | Server proxy to the backend |
| [`components/MessageBubble.tsx`](../frontend/components/MessageBubble.tsx) | A message + typing indicator |
| [`components/SuggestedQuestions.tsx`](../frontend/components/SuggestedQuestions.tsx) | The starter chips |
| [`lib/api.ts`](../frontend/lib/api.ts) | `sendChat()` helper |

## The proxy route — why it exists

The browser never talks to the backend directly. It calls **our own** `/api/chat`, which forwards to the
FastAPI `api`. Three reasons:

1. **Hide the backend URL** — `BACKEND_URL` stays a server-only env var.
2. **No CORS headaches** — same origin.
3. **Correct rate limiting** — the proxy reads the real client IP from `x-forwarded-for` (Cloud Run sets
   it) and passes it on, so the backend rate-limits *per recruiter*, not per frontend instance.

```ts
const clientIp = req.headers.get("x-forwarded-for")?.split(",")[0].trim() ?? "unknown";
fetch(`${BACKEND_URL}/chat`, { headers: { "x-forwarded-for": clientIp }, ... });
```

## The chat screen

`page.tsx` is a client component holding `messages`, `input`, and `loading`. The `ask()` function:

1. optimistically appends the user's message,
2. sends `{ message, history }` (history = prior turns for follow-up context),
3. appends the reply, or a friendly error if the request fails,
4. shows a typing indicator while `loading`.

Answers render as Markdown (`react-markdown`) so bullet lists and bold text look right.

## Customizing the look

- **Bot name:** `BOT_NAME` in `app/page.tsx`.
- **Accent color:** `accent` in `tailwind.config.ts`.
- **Suggested questions:** the `SUGGESTED` array in `components/SuggestedQuestions.tsx`.

## Run it

```bash
cd frontend
npm install
echo "BACKEND_URL=http://localhost:8000" > .env
npm run dev   # http://localhost:3000
```

`npm run build` produces a **standalone** output (small Docker image) — see [07](07-deploy-cloud-run.md).

Next: [06 — Redis VM](06-redis-vm.md).
