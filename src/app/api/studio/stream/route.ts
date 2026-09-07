import { db } from "@/lib/db";
import { bad } from "@/lib/api";
import { getStudioSession } from "@/lib/users";
import { buildAgentTrace } from "@/lib/agenttrace";
import { queuePositionFor } from "@/lib/subs";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const TICK_MS = 2000; // trace refresh cadence
const MAX_LIFETIME_MS = 30 * 60 * 1000; // hard cap per connection — no runaway streams

/**
 * GET /api/studio/stream?requestId=… — Server-Sent Events live film simulator.
 *
 * Streams the agent trace for one VideoRequest to its owner (or any admin):
 * `event: trace` carries the full deterministic timeline each tick; a terminal
 * `event: end` closes the stream when the render reaches done/failed/cancelled
 * (or after the lifetime cap — the client simply reconnects if it wants more).
 *
 * Auth: user session cookie (same model as /api/studio/render). Ownership is
 * enforced server-side: request.email must match the session email, admins
 * may watch anything.
 */
export async function GET(req: Request) {
  const s = await getStudioSession();
  if (s.kind === "anon") return bad("Sign in required", 401);
  if (s.kind === "blocked") return bad(`Account ${s.status}: ${s.reason}`, 403);

  const requestId = (new URL(req.url).searchParams.get("requestId") || "").slice(0, 40);
  if (!requestId) return bad("requestId is required");

  const request = await db.videoRequest.findUnique({ where: { id: requestId } });
  if (!request) return bad("Request not found", 404);
  if (s.user.role !== "admin" && request.email !== s.user.email) {
    return bad("This render belongs to another account", 403);
  }

  // Linked studio project gives the trace real scene titles + cast names.
  let scriptJson: string | null = null;
  const m = /^studio:([^:]+)(?::|$)/.exec(request.notes || "");
  if (m?.[1] && m[1] !== "studio") {
    const project = await db.studioProject.findUnique({ where: { id: m[1] } });
    if (project) scriptJson = project.scriptJson;
  }

  const encoder = new TextEncoder();
  const startedAt = Date.now();

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      let closed = false;
      const send = (event: string, data: unknown) => {
        if (closed) return;
        try {
          controller.enqueue(encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`));
        } catch {
          closed = true;
        }
      };
      const stop = () => {
        if (closed) return;
        closed = true;
        try {
          controller.close();
        } catch {
          /* already closed */
        }
      };
      req.signal.addEventListener("abort", stop);

      // Ask EventSource to wait 10s before reconnecting after an intentional close.
      if (!closed) {
        try {
          controller.enqueue(encoder.encode("retry: 10000\n\n"));
        } catch {
          closed = true;
        }
      }

      try {
        while (!closed) {
          const fresh = await db.videoRequest.findUnique({ where: { id: requestId } });
          if (!fresh) {
            send("end", { status: "gone" });
            stop();
            break;
          }
          const queuePosition = fresh.status === "queued" ? await queuePositionFor(fresh) : null;
          send("trace", buildAgentTrace({ request: fresh, scriptJson, queuePosition, now: Date.now() }));

          if (["done", "failed", "cancelled"].includes(fresh.status)) {
            send("end", { status: fresh.status });
            stop();
            break;
          }
          if (Date.now() - startedAt > MAX_LIFETIME_MS) {
            send("end", { status: "timeout" });
            stop();
            break;
          }
          await new Promise((r) => setTimeout(r, TICK_MS));
        }
      } catch {
        // DB hiccup or aborted stream — close cleanly; the client reconnects.
        stop();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
