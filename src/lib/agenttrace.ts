/**
 * Agent trace engine — the brain behind the live film simulator.
 *
 * Given a VideoRequest (plus its optional StudioProject script), it derives the
 * exact storyboard-execution timeline the UI streams to the user: brief parsed,
 * characters cast, scenes storyboarded, GPU queue, per-scene render passes,
 * assembly and delivery.
 *
 * Design guarantees:
 * - DETERMINISTIC: the timeline is a pure function of (request row, script,
 *   now). Server restarts, multiple SSE viewers or reconnects always produce
 *   the same trace for the same moment in time — no state is stored anywhere.
 * - HONEST: real fleet transitions (queued -> rendering -> done/failed) drive
 *   the phase changes. Only the pacing *within* a phase is simulated, and the
 *   UI labels it as such. Nothing ever shows a finished film before the worker
 *   actually delivers one (prompt §65 — no fake success).
 */

export type TraceStepState = "done" | "active" | "pending" | "failed";

export type TraceStep = {
  id: string;
  label: string;
  detail?: string;
  state: TraceStepState;
  /** Seconds after submission when this step became active (time gutter). */
  t?: number;
};

export type TracePhase = "agent" | "queue" | "gpu" | "closed";

export type AgentTrace = {
  requestId: string;
  status: string;
  phase: TracePhase;
  headline: string;
  steps: TraceStep[];
  resultUrl?: string;
  failedReason?: string;
  /** Whole seconds since the request was submitted. */
  elapsedSec: number;
};

export type TraceRequest = {
  id: string;
  prompt: string;
  seconds: number;
  resolution: string;
  withAudio: boolean;
  status: string; // queued | rendering | done | failed | cancelled
  notes: string;
  resultUrl?: string;
  createdAt: Date | string;
};

type TraceScript = {
  characters?: { name: string; look?: string; voice?: string }[];
  scenes?: { id: string; title?: string; seconds?: number; visual?: string; line?: string }[];
};

/* ---------- pacing constants (simulated, phase-internal only) ---------- */
const AGENT_STEP_MS = 1600; // each pre-GPU agent step takes ~1.6s of wall time
const GPU_STEP_MS = 90_000; // each GPU pass step gets a ~90s slot

const clamp = (s: string | undefined | null, n: number) => {
  const t = (s ?? "").trim();
  if (!t) return undefined;
  return t.length > n ? t.slice(0, n - 1) + "…" : t;
};

/** "claimed by deyoung-v2-s01 at 2026-09-07T02:12:00Z" -> epoch ms of claim. */
function claimTimeFromNotes(notes: string, fallback: number): number {
  const m = /claimed by .+ at (.+)$/m.exec(notes || "");
  if (m) {
    const t = Date.parse(m[1]);
    if (Number.isFinite(t)) return t;
  }
  return fallback;
}

function parseScript(scriptJson: string | null | undefined): TraceScript | null {
  if (!scriptJson) return null;
  try {
    const s = JSON.parse(scriptJson) as TraceScript;
    if (s && (Array.isArray(s.scenes) || Array.isArray(s.characters))) return s;
  } catch {
    /* draft project without a valid script */
  }
  return null;
}

type BuiltSteps = { steps: TraceStep[]; gpuStepIds: string[]; phase: TracePhase; failedReason?: string };

function buildSteps(
  req: TraceRequest,
  script: TraceScript | null,
  queuePosition: number | null,
  now: number
): BuiltSteps {
  const createdAt = Date.parse(String(req.createdAt));
  const elapsed = Math.max(0, now - createdAt);
  const done = req.status === "done";
  const failed = req.status === "failed";
  const cancelled = req.status === "cancelled";
  const closed = done || failed || cancelled;
  const rendering = req.status === "rendering";

  const steps: TraceStep[] = [];
  const push = (id: string, label: string, detail: string | undefined, state: TraceStepState, t?: number) =>
    steps.push({ id, label, detail, state, t });

  /* ----- phase A: the agent plans (always runs, fast clock) ----- */
  const cast = (script?.characters ?? []).map((c) => c.name).filter(Boolean) as string[];
  const scenes = script?.scenes ?? [];
  const totalSceneSec = scenes.reduce((a, s) => a + (s.seconds ?? 0), 0);

  push("brief", "Brief received", clamp(req.prompt, 110), "done", 0);
  push("parse", "Parsing prompt", "style · motion · mood extracted", "done", 1);
  push("cast", "Casting characters", cast.length ? cast.join(" · ") : "single-shot plan — no cast needed", "done", 2);
  push(
    "storyboard",
    "Storyboarding",
    scenes.length
      ? `${scenes.length} scene${scenes.length > 1 ? "s" : ""} · ${totalSceneSec || req.seconds}s runtime`
      : `single shot · ${req.seconds}s runtime`,
    "done",
    3
  );

  /* ----- phase B: GPU queue (driven by real status) ----- */
  const pastQueue = req.status !== "queued";
  push(
    "queue",
    "Waiting for a GPU slot",
    pastQueue ? "slot assigned" : `position #${queuePosition || 1} · fleet checks every 60s`,
    pastQueue ? "done" : "active",
    pastQueue ? 4 : undefined
  );

  /* ----- phase C: GPU render passes (real claim time, simulated pacing) ----- */
  const gpuStepIds: string[] = [];
  if (scenes.length) {
    for (const sc of scenes) {
      gpuStepIds.push(`scene:${sc.id}`);
      push(
        `scene:${sc.id}`,
        `Scene ${sc.id}${sc.title ? ` — ${sc.title}` : ""}`,
        clamp(sc.visual || sc.line, 90),
        "pending"
      );
    }
  } else {
    gpuStepIds.push("diffusion");
    push("diffusion", "Rendering film", `${req.seconds}s · ${req.resolution} diffusion pass`, "pending");
  }
  gpuStepIds.push("motion");
  push("motion", "Motion & camera pass", "blocking · camera moves · cuts", "pending");
  if (req.withAudio) {
    gpuStepIds.push("audio");
    push("audio", "Audio bed & mix", "score + dialogue levelling", "pending");
  }
  gpuStepIds.push("grade");
  push("grade", "Upscale & color grade", `master at ${req.resolution}`, "pending");

  if (closed) {
    for (const id of gpuStepIds) {
      const s = steps.find((x) => x.id === id);
      if (s) s.state = "done";
    }
  } else if (rendering || pastQueue) {
    const claimAt = claimTimeFromNotes(req.notes, createdAt);
    const gpuElapsed = Math.max(0, now - claimAt);
    const activeIdx = rendering ? Math.min(Math.floor(gpuElapsed / GPU_STEP_MS), gpuStepIds.length - 1) : -1;
    steps.forEach((s) => {
      const gi = gpuStepIds.indexOf(s.id);
      if (gi === -1) return;
      if (gi < activeIdx) {
        s.state = "done";
      } else if (gi === activeIdx) {
        s.state = "active";
        s.t = Math.round((claimAt - createdAt) / 1000) + gi * (GPU_STEP_MS / 1000);
      } else {
        s.state = "pending";
      }
    });
  }

  /* ----- phase D: delivery (real status only) ----- */
  push(
    "encode",
    "Encode & upload",
    done ? "master stored — private by default" : undefined,
    done ? "done" : "pending"
  );
  push(
    "deliver",
    done ? "Delivered — film ready" : "Delivery",
    done ? "watch from the dashboard or the studio" : undefined,
    done ? "done" : "pending"
  );

  /* ----- failure / cancellation overlays ----- */
  let failedReason: string | undefined;
  if (failed) {
    failedReason = clamp((req.notes || "").replace(/\s*— reported by .+$/, ""), 140) || "render failed";
    const active = steps.find((s) => s.state === "active");
    if (active) active.state = "failed";
    push("failed", "Render failed", failedReason, "failed");
  }
  if (cancelled) {
    push("cancelled", "Request cancelled", undefined, "failed");
  }

  /* ----- phase resolution ----- */
  let phase: TracePhase = "agent";
  if (closed) phase = "closed";
  else if (rendering) phase = "gpu";
  else if (pastQueue) phase = "gpu"; // claimed note not yet visible — GPU side owns it now
  else if (elapsed > 4 * AGENT_STEP_MS) phase = "queue";

  return { steps, gpuStepIds, phase, failedReason };
}

export function buildAgentTrace(input: {
  request: TraceRequest;
  scriptJson?: string | null;
  queuePosition?: number | null;
  now?: number;
}): AgentTrace {
  const now = input.now ?? Date.now();
  const script = parseScript(input.scriptJson);
  const { steps, phase, failedReason } = buildSteps(input.request, script, input.queuePosition ?? null, now);

  const headline =
    input.request.status === "done"
      ? "Delivery complete — your film is ready"
      : input.request.status === "failed"
        ? "The render hit a snag — the owner can requeue it"
        : input.request.status === "cancelled"
          ? "Request cancelled"
          : input.request.status === "rendering"
            ? "GPUs are rendering your film"
            : phase === "queue"
              ? "In the GPU queue — the fleet cycles every minute"
              : "The agent is building your film";

  const createdAt = Date.parse(String(input.request.createdAt));
  return {
    requestId: input.request.id,
    status: input.request.status,
    phase,
    headline,
    steps,
    resultUrl: input.request.status === "done" ? input.request.resultUrl || undefined : undefined,
    failedReason,
    elapsedSec: Math.round(Math.max(0, now - createdAt) / 1000),
  };
}
