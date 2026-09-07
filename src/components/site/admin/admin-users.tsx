"use client";

import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/types";
import { toast } from "sonner";
import { Loader2, Search, ShieldBan, ShieldCheck, ShieldOff, ShieldPlus, ShieldX } from "lucide-react";

type Row = {
  id: string;
  email: string;
  name: string;
  role: string;
  status: string;
  banReason: string;
  provider: string;
  image: string;
  createdAt: string;
  lastLoginAt: string | null;
  subscription: { planCode: string; periodEnd: string | null } | null;
  videosUsed: number;
};

/** W2: full user control — search, ban / activate / deactivate, admin grant/revoke. */
export function AdminUsers() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [q, setQ] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async (query = "") => {
    try {
      const d = await api<{ users: Row[] }>(`/api/admin/users?q=${encodeURIComponent(query)}`);
      setRows(d.users);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not load users");
      setRows([]);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  async function act(id: string, action: string, reason?: string) {
    if (action === "ban" && !reason) {
      const r = window.prompt("Ban reason (shown to the user when they try to sign in):");
      if (!r) return;
      reason = r;
    }
    setBusyId(id);
    try {
      await api(`/api/admin/users/${id}`, { method: "PATCH", body: JSON.stringify({ action, reason }) });
      toast.success(`Done: ${action.replace("-", " ")}`);
      await load(q);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-black uppercase">Users</h2>
          <p className="text-sm text-muted-foreground">
            Every account — ban, deactivate, reactivate, grant or revoke admin. Banned users fail closed at sign-in.
          </p>
        </div>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            load(q);
          }}
        >
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search email or name" className="w-56" aria-label="Search users" />
          <Button type="submit" variant="outline">
            <Search className="h-4 w-4" aria-hidden /> Search
          </Button>
        </form>
      </div>

      {rows === null ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-primary" aria-label="Loading users" />
        </div>
      ) : rows.length === 0 ? (
        <p className="py-16 text-center text-muted-foreground">No users match.</p>
      ) : (
        <div className="mt-6 space-y-3">
          {rows.map((u) => (
            <div key={u.id} className="rounded-xl border bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-black">{u.name || "—"} <span className="font-mono text-xs font-normal text-muted-foreground">{u.email}</span></p>
                    {u.role === "admin" && <Badge className="bg-primary text-white">admin</Badge>}
                    <Badge variant="outline" className={u.status === "active" ? "border-emerald-300 text-emerald-700" : "border-red-300 text-red-700"}>
                      {u.status}
                    </Badge>
                    {u.provider === "google" && <Badge variant="outline">google</Badge>}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {u.subscription ? `plan: ${u.subscription.planCode}` : "no plan"} · {u.videosUsed} render{u.videosUsed === 1 ? "" : "s"} ·
                    joined {new Date(u.createdAt).toLocaleDateString()}
                    {u.lastLoginAt ? ` · last seen ${new Date(u.lastLoginAt).toLocaleDateString()}` : ""}
                    {u.banReason ? ` · reason: ${u.banReason}` : ""}
                  </p>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {busyId === u.id ? (
                    <Loader2 className="h-5 w-5 animate-spin text-primary" aria-label="Working" />
                  ) : (
                    <>
                      {u.status !== "active" && (
                        <Button size="sm" variant="outline" onClick={() => act(u.id, "activate")} className="border-emerald-300 text-emerald-700 hover:bg-emerald-50">
                          <ShieldCheck className="h-4 w-4" aria-hidden /> Activate
                        </Button>
                      )}
                      {u.status === "active" && (
                        <>
                          <Button size="sm" variant="outline" onClick={() => act(u.id, "deactivate")} className="border-amber-300 text-amber-700 hover:bg-amber-50">
                            <ShieldOff className="h-4 w-4" aria-hidden /> Deactivate
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => act(u.id, "ban")} className="border-red-300 text-red-700 hover:bg-red-50">
                            <ShieldBan className="h-4 w-4" aria-hidden /> Ban
                          </Button>
                        </>
                      )}
                      {u.role !== "admin" ? (
                        <Button size="sm" variant="outline" onClick={() => act(u.id, "make-admin")} className="border-neutral-300">
                          <ShieldPlus className="h-4 w-4" aria-hidden /> Make admin
                        </Button>
                      ) : (
                        <Button size="sm" variant="outline" onClick={() => act(u.id, "remove-admin")} className="border-neutral-300">
                          <ShieldX className="h-4 w-4" aria-hidden /> Revoke admin
                        </Button>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
