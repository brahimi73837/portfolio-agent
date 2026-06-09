// Slash commands: deterministic, instant, NO AI call. Responses are pre-written
// from the knowledge base so they're accurate and free. Rendered as normal
// assistant messages (Markdown).

export interface SlashCommand {
  name: string;
  description: string;
  response: string;
}

// Order here = order shown in /help.
const LIST: SlashCommand[] = [
  {
    name: "about",
    description: "Quick intro to Brahim",
    response:
      "**Brahim Elkhattabi** — AI Engineer / Software Developer.\n\n" +
      "23, final-year BSc Software Development student at MCAST (Malta), graduating Nov 2026. " +
      "He builds real, deployed projects with LLMs, RAG pipelines, MCP servers, and modern web stacks — " +
      "and has a year of professional experience as a Junior Data Support apprentice.\n\n" +
      "Try `/projects`, `/skills`, `/experience`, or `/contact`.",
  },
  {
    name: "projects",
    description: "List Brahim's projects with links",
    response:
      "Here are Brahim's main projects:\n\n" +
      "**1. Garmin NLP Workouts** — turns natural-language workout descriptions into structured Garmin " +
      "workouts via the Gemini API.\n" +
      "→ [GitHub](https://github.com/brahimi73837/garmin-workout-full-stack)\n\n" +
      "**2. Flight Deck** — spec-first flight search + fare tracker with a Gemini AI assistant over a " +
      "Python FastMCP server.\n" +
      "→ [GitHub](https://github.com/brahimi73837/flight_mcp)\n\n" +
      "**3. Mezzo** — production GCP app that turns menu photos into a multilingual, searchable catalogue " +
      "(Vision AI, Cloud Functions, Terraform).\n" +
      "→ [GitHub](https://github.com/brahimi73837/cloud-based-restaurant-menu-OCR-system)\n\n" +
      "**4. CabBook** — five-service microservices cab-booking platform with event-driven flows.\n" +
      "→ [GitHub](https://github.com/brahimi73837/Cab-Booking-Microservices-Final) · " +
      "[Live demo](https://cab-booking-microservices-web.vercel.app)\n\n" +
      "**5. Agentic RAG (Dissertation)** — fact-checks health claims against scientific literature " +
      "(Qwen2.5-7B, MedCPT, FAISS, MultiVerS).\n\n" +
      "Ask me about any one for the full story!",
  },
  {
    name: "skills",
    description: "Brahim's tech stack",
    response:
      "**Brahim's tech stack:**\n\n" +
      "- **Languages:** Python, JavaScript/TypeScript, SQL\n" +
      "- **AI / ML:** Gemini API, LangChain, RAG, vector DBs (FAISS), MCP servers, prompt engineering & caching\n" +
      "- **Backend:** FastAPI, Node.js + Express, PostgreSQL / MySQL / MongoDB, REST + Swagger\n" +
      "- **Frontend:** Next.js (App Router), React, Tailwind CSS, TypeScript\n" +
      "- **Cloud / DevOps:** Google Cloud (Cloud Run, Cloud Functions, Firestore, Pub/Sub, Vision AI, Secret Manager), Terraform, Azure Databricks, Redis, Git\n\n" +
      "Currently going deeper on AI agents & LangGraph.",
  },
  {
    name: "experience",
    description: "Work experience",
    response:
      "**Junior Data Support (Apprenticeship)** — O|Tech · Malta · Jan 2024 – Feb 2025\n\n" +
      "- Monitored & maintained company databases (SQL, Python) for data quality\n" +
      "- Built internal dashboards in Azure Databricks for monitoring & analysis\n" +
      "- Automated data validation & cleanup to cut manual work\n" +
      "- Wrote technical docs and supported data, operations, and QA teams\n\n" +
      "He's now a final-year student available to start once interviews & paperwork are done.",
  },
  {
    name: "contact",
    description: "How to reach Brahim",
    response:
      "**Get in touch with Brahim:**\n\n" +
      "- 📧 Email: [brahimelkhattabi88@gmail.com](mailto:brahimelkhattabi88@gmail.com)\n" +
      "- 🎓 College email: [brahim.el.i73837@mcast.edu.mt](mailto:brahim.el.i73837@mcast.edu.mt)\n" +
      "- 💻 GitHub: [github.com/brahimi73837](https://github.com/brahimi73837)\n" +
      "- 💼 LinkedIn: coming soon\n\n" +
      "Resume available on request. Email is the best way to reach him.",
  },
  {
    name: "github",
    description: "Brahim's GitHub profile",
    response:
      "Brahim's GitHub: **[github.com/brahimi73837](https://github.com/brahimi73837)** — " +
      "you'll find the projects above there.",
  },
];

export const COMMANDS: Record<string, SlashCommand> = Object.fromEntries(
  LIST.map((c) => [c.name, c]),
);

// /help is generated from the list so it never drifts out of sync.
const HELP: SlashCommand = {
  name: "help",
  description: "Show all slash commands",
  response:
    "**Available commands** — type one and press Enter for an instant answer:\n\n" +
    LIST.map((c) => `- \`/${c.name}\` — ${c.description}`).join("\n") +
    "\n- `/help` — show this list\n\n" +
    "Or just ask me anything about Brahim in plain English.",
};
COMMANDS.help = HELP;

export const UNKNOWN_COMMAND_RESPONSE =
  "I don't recognize that command 🤔 — type `/help` to see what I can do, " +
  "or just ask me anything about Brahim.";

/**
 * Returns the matching command, the string "unknown" for an unrecognized slash
 * command, or null when the input isn't a slash command at all.
 */
export function resolveCommand(input: string): SlashCommand | "unknown" | null {
  const t = input.trim();
  if (!t.startsWith("/")) return null;
  const name = t.slice(1).split(/\s+/)[0].toLowerCase();
  return COMMANDS[name] ?? "unknown";
}
