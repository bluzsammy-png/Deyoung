"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft, Loader2, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, type SupportMsg } from "@/lib/types";

type Thread = { userId: string; userEmail: string; last: string; unread: number; count: number };

/** Admin live-support inbox: thread list + conversation with reply. */
export function AdminSupport() {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [active, setActive] = useState<Thread | null>(null);
  const [messages, setMessages] = useState<SupportMsg[]>([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  const loadThreads = useCallback(() => {
    api<{ threads: Thread[] }>("/api/admin/support")
      .then((r) => setThreads(r.threads))
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadThreads();
    const t = setInterval(loadThreads, 6000);
    return () => clearInterval(t);
  }, [loadThreads]);

  const loadMessages = useCallback((userId: string) => {
    api<{ messages: SupportMsg[] }>("/api/support/messages-by-user", { method: "POST", body: JSON.stringify({ userId }) })
      .then((r) => setMessages(r.messages))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!active) return;
    loadMessages(active.userId);
    const t = setInterval(() => loadMessages(active.userId), 4000);
    return () => clearInterval(t);
  }, [active, loadMessages]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!active || !text.trim()) return;
    setSending(true);
    const body = text.trim();
    setText("");
    try {
      await api("/api/admin/support", { method: "POST", body: JSON.stringify({ userId: active.userId, body }) });
      loadMessages(active.userId);
      loadThreads();
    } finally {
      setSending(false);
    }
  }

  if (active) {
    return (
      <div className="max-w-2xl">
        <button onClick={() => setActive(null)} className="inline-flex items-center gap-2 text-sm font-bold text-primary hover:underline">
          <ArrowLeft className="h-4 w-4" aria-hidden /> All conversations
        </button>
        <p className="mt-2 text-sm font-black">{active.userEmail}</p>
        <div className="mt-4 border-2 border-border">
          <div className="h-[400px] overflow-y-auto p-4 space-y-3 bg-muted/30">
            {messages.map((m) => (
              <div key={m.id} className={`flex ${m.fromUser ? "justify-start" : "justify-end"}`}>
                <div className={`max-w-[80%] px-3.5 py-2.5 text-sm leading-relaxed ${
                  m.fromUser ? "bg-white border-2 border-border" : "bg-primary text-white"
                }`}>
                  {m.body}
                  <span className={`block mt-1 text-[10px] ${m.fromUser ? "text-muted-foreground" : "text-white/70"}`}>
                    {new Date(m.createdAt).toLocaleString()}
                  </span>
                </div>
              </div>
            ))}
            <div ref={endRef} />
          </div>
          <form onSubmit={send} className="p-3 border-t-2 border-border flex gap-2 bg-white">
            <Input value={text} onChange={(e) => setText(e.target.value)} placeholder="Reply to the customer…" aria-label="Reply" />
            <Button type="submit" disabled={sending || !text.trim()} className="bg-primary hover:bg-[#B91C1C] text-white font-bold">
              {sending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Send className="h-4 w-4" aria-hidden />}
            </Button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">Customer conversations from the studio&apos;s live support tab. Unread customer messages are flagged.</p>
      {threads.length === 0 ? (
        <p className="border border-dashed border-border p-8 text-center text-sm text-muted-foreground">No conversations yet.</p>
      ) : (
        threads.map((t) => (
          <button
            key={t.userId}
            onClick={() => setActive(t)}
            className="w-full text-left border-2 border-border bg-white px-4 py-3 hover:border-primary transition-colors flex items-center gap-3"
          >
            <span className="h-9 w-9 grid place-items-center bg-[var(--brand-black)] text-white font-black uppercase shrink-0">
              {t.userEmail.slice(0, 1).toUpperCase()}
            </span>
            <span className="flex-1 min-w-0">
              <span className="block text-sm font-bold truncate">{t.userEmail}</span>
              <span className="block text-xs text-muted-foreground">{t.count} messages · last {new Date(t.last).toLocaleString()}</span>
            </span>
            {t.unread > 0 && (
              <span className="bg-primary text-white text-[10px] font-black uppercase tracking-widest px-2 py-1 shrink-0">
                {t.unread} new
              </span>
            )}
          </button>
        ))
      )}
    </div>
  );
}
