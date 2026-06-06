// Server-side proxy to the FastAPI backend.
// Why a proxy: keeps BACKEND_URL server-only, avoids CORS, and lets us forward the
// REAL client IP so the backend's per-IP rate limiting works correctly.

import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ reply: "Invalid request." }, { status: 400 });
  }

  // Real client IP: Cloud Run / proxies set x-forwarded-for to the caller.
  const clientIp =
    req.headers.get("x-forwarded-for")?.split(",")[0].trim() ||
    req.headers.get("x-real-ip") ||
    "unknown";

  try {
    const upstream = await fetch(`${BACKEND_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-forwarded-for": clientIp, // backend reads first hop as the recruiter's IP
      },
      body: JSON.stringify(body),
      // The backend is fast; cap the wait so the UI never hangs.
      signal: AbortSignal.timeout(30_000),
    });
    const data = await upstream.json();
    return NextResponse.json(data, { status: upstream.status });
  } catch {
    return NextResponse.json(
      { reply: "I had trouble reaching my brain just now — please try again.", source: "error" },
      { status: 502 },
    );
  }
}
