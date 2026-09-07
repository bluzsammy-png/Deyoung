"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Check, ExternalLink, Loader2, Radio, X } from "lucide-react";
import type { AgentTrace, TraceStep } from "@/lib/agenttrace";

/**
 * Live film simulator console — streams one render's agent timeline over SSE
 * (/api/studio/stream). Every storyboard line is drawn connected to the next:
 * done nodes fill, the active node pulses, and the real fleet status drives
 * the phase. Terminal states stay on screen until the viewer closes them.
 */

const STATE_STYLE: Record<TraceStep["state"], { node: string; line: string }> = {
  done: { node: "border-primary bg-primary text-white", line: "border-primary/60" },
  active: { node: "border-amber-400 bg-amber-400/20 text-amber-300 animate-pulse", line: "border-white/15" },
  pending: { node: "border-white/20 bg-transparent text-transparent", line: "border-white/10" },
  failed: { node: "border-red-500 bg-red-500/20 text-red-400", line: "border-red-500/40" },
};

function mmss(totalSec: number): string {
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function StepRow({ step, last }: { step: TraceStep; last: boolean }) {
  const st = STATE_STYLE[step.state];
  return (
    <div className="flex gap-3">
      {/* time gutter + connected node + connector line */}
      <div className="flex w-12 shrink-0 justify-end pt-0.5">
        <span className={`font-mono text-[11px] ${step.state === "pending" ? "text-white/25" : "text-white/50"}`}>
          {step.t !== undefined ? mmss(step.t) : "--:--"}
        </span>
      </div>
      <div className="flex flex-col items-center">
        <span className={`mt-1 flex h-4 w-4 items-center justify-center rounded-full border ${st.node}`} aria-hidden>
          {step.state === "done" && <Check className="h-2.5 w-2.5" strokeWidth={3.5} />}
        </span>
        {!last && <span className={`my-0.5 w-px flex-1 border-l-2 border-dashed ${st.line}`} aria-hidden />}
      </div>
      <div className={`pb-4 ${last ? "pb-0" : ""}`}>
        <p className={`text-sm font-bold leading-snug ${
          step.state === "pending" ? "text-white/35" :
          step.state === "failed" ? "text-red-400" :
          step.state === "active" ? "text-white" : "text-white/75"
        }`}>
          {step.label}
          {step.state === "active" && (
            <Loader2 className="ml-1.5 inline h-3.5 w-3.5 animate-spin text-amber-300" aria-hidden />
          )}
        </p>
        {step.detail && <p className={`mt-0.5 text-xs leading-relaxed ${step.state === "pending" ? "text-white/25" : "text-white/45"}`}>{step.detail}</p>}
      </div>
    </div>
  );
}

export function AgentStream({ requestId, onClose }: { requestId: string; onClose: () => void }) {
  const [trace, setTrace] = useState<AgentTrace | null>(null);
  const [ended, setEnded] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const es = new EventSource(`/api/studio/stream?requestId=${encodeURIComponent(requestId)}`);
    es.addEventListener("trace", (e) => {
      try {
        setTrace(JSON.parse((e as MessageEvent).data) as AgentTrace);
      } catch {
        /* ignore malformed frame */
      }
    });
    es.addEventListener("end", () => {
      setEnded(true);
      es.close();
    });
    es.onerror = () => {
      // EventSource retries automatically (server asked for 10s); if the
      // stream is gone for good the next end/retry cycle resolves it.
    };
    return () => es.close();
  }, [requestId]);

  const activeId = trace?.steps.find((s) => s.state === "active")?.id;
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [activeId]);

  const terminal = trace && ["done", "failed", "cancelled"].includes(trace.status);

  return (
    <div className="overflow-hidden rounded-2xl border border-white/10 bg-black/50" data-testid="agent-stream">
      {/* header */}
      <div className="flex items-center justify-between gap-3 border-b border-white/10 bg-white/[0.03] px-4 py-3">
        <div className="flex min-w-0 items-center gap-2.5">
          <span className={`flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-black uppercase tracking-widest ${
            trace && !terminal
              ? "border-red-500/40 bg-red-500/10 text-red-400"
              : "border-white/15 text-white/50"
          }`}>
            <Radio className={`h-3 w-3 ${trace && !terminal ? "animate-pulse" : ""}`} aria-hidden />
            {trace && !terminal ? "Live" : "Ended"}
          </span>
          <p className="truncate text-sm font-bold text-white/85">{trace?.headline ?? "Connecting to the agent…"}</p>
        </div>
        <button onClick={onClose} aria-label="Close live view" className="rounded-lg p-1.5 text-white/40 hover:bg-white/10 hover:text-white">
          <X className="h-4 w-4" aria-hidden />
        </button>
      </div>

      {/* body */}
      <div ref={scrollRef} className="max-h-96 overflow-y-auto px-4 py-4 [scrollbar-width:thin]">
        {!trace ? (
          <div className="flex items-center justify-center gap-2 py-8 text-sm text-white/40">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> Handshaking with the render farm…
          </div>
        ) : (
          <div className="flex flex-col">
            {trace.steps.map((s, i) => (
              <StepRow key={s.id} step={s} last={i === trace.steps.length - 1} />
            ))}
          </div>
        )}
      </div>

      {/* footer */}
      <div className="border-t border-white/10 bg-white/[0.02] px-4 py-3">
        {trace?.status === "done" && trace.resultUrl && (
          <div className="mb-3 flex flex-wrap items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3">
            <Check className="h-4 w-4 text-emerald-400" aria-hidden />
            <span className="text-sm font-bold text-emerald-300">Delivery complete</span>
            <a href={trace.resultUrl} target="_blank" rel="noreferrer">
              <Button size="sm" className="ml-auto bg-emerald-600 font-bold text-white hover:bg-emerald-500">
                Watch now <ExternalLink className="ml-1 h-3.5 w-3.5" aria-hidden />
              </Button>
            </a>
          </div>
        )}
        {trace?.failedReason && (
          <p className="mb-3 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
            {trace.failedReason}
          </p>
        )}
        <p className="text-[11px] leading-relaxed text-white/30">
          Agent timeline · pacing simulated, status real — QUEUED / RENDERING / DONE come straight from the GPU fleet.
          {ended && !terminal ? " Stream closed (30-min cap) — reopen to continue watching." : ""}
        </p>
      </div>
    </div>
  );
}
