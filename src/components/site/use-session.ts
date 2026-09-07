"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/types";

export type SessionInfo = {
  user: { id: string; email: string; name: string; image: string; role: string } | null;
  userBlocked: { status: string; reason: string } | null;
  admin: { email: string } | null;
};

/** Shared session probe (header + dashboard + studio). Re-probes on route change. */
export function useSessionBadge(): SessionInfo | null {
  const [session, setSession] = useState<SessionInfo | null>(null);
  useEffect(() => {
    let alive = true;
    const load = () =>
      api<SessionInfo>("/api/auth/session")
        .then((s) => alive && setSession(s))
        .catch(() => alive && setSession({ user: null, userBlocked: null, admin: null }));
    load();
    // hash navigation does not remount the header — re-probe on every route change
    window.addEventListener("hashchange", load);
    return () => {
      alive = false;
      window.removeEventListener("hashchange", load);
    };
  }, []);
  return session;
}

export async function signOutUser(): Promise<void> {
  await api("/api/auth/user-logout", { method: "POST" });
}
