// Live answers for the public demo. Builds the prompt itself from the fixed evidence packs, so it answers
// questions about the demo's clients and nothing else. The page still checks every figure in the answer.
import Anthropic from "@anthropic-ai/sdk";
import { PACKS, prompt } from "./_evidence.mjs";

const client = new Anthropic(); // reads ANTHROPIC_API_KEY from the Vercel project's environment
const hits = new Map();          // per-instance rate limit: 30 questions per visitor per hour
const LIMIT = 30, WINDOW = 60 * 60 * 1000;

const ANSWER = {
  type: "object",
  properties: { answer: { type: "string" }, cites: { type: "array", items: { type: "string" } }, answerable: { type: "boolean" } },
  required: ["answer", "cites", "answerable"],
  additionalProperties: false,
};
const clip = (v, n) => String(v ?? "").slice(0, n);

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).json({ error: "POST only" });
  if (!process.env.ANTHROPIC_API_KEY) return res.status(503).json({ error: "live answers are not configured" });
  const ip = String(req.headers["x-forwarded-for"] || "").split(",")[0].trim() || "unknown";
  const now = Date.now();
  const recent = (hits.get(ip) || []).filter((t) => now - t < WINDOW);
  if (recent.length >= LIMIT) return res.status(429).json({ error: "too many questions; try again later" });
  hits.set(ip, [...recent, now]);

  const body = typeof req.body === "string" ? JSON.parse(req.body || "{}") : req.body || {};
  const ctx = String(body.ctx || "");
  const q = clip(body.q, 500).trim();
  if (!PACKS[ctx] || !q) return res.status(400).json({ error: "unknown client or empty question" });
  const history = (Array.isArray(body.history) ? body.history : []).slice(-3).map((h) => ({ q: clip(h.q, 500), answer: clip(h.answer, 1200) }));
  const retryNote = clip(body.retryNote, 300);

  try {
    const msg = await client.messages.create({
      model: "claude-haiku-5-5",
      max_tokens: 5000,
      output_config: { effort: "low", format: { type: "json_schema", schema: ANSWER } },
      messages: [{ role: "user", content: prompt(ctx, q, history, retryNote) }],
    });
    const text = msg.content.filter((b) => b.type === "text").map((b) => b.text).join("");
    const i = text.indexOf("{"), j = text.lastIndexOf("}");
    const out = JSON.parse(text.slice(i, j + 1));
    return res.status(200).json({ answer: String(out.answer || ""), cites: Array.isArray(out.cites) ? out.cites.map(String) : [], answerable: out.answerable !== false });
  } catch (e) {
    console.error("ask failed", e?.status || "", e?.message || e);
    return res.status(502).json({ error: "the model call failed" });
  }
}
