"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ArrowLeft, BarChart3, CalendarCheck, Camera, Clapperboard, Film, Image as ImageIcon, LayoutDashboard, Lock, LogOut,
  Mail, MessageSquareQuote, Mic, RadioTower, Settings as SettingsIcon, ShieldAlert, Sparkles, Users, Wallet, X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { api, money, type Booking } from "@/lib/types";
import { go } from "../hash";
import {
  AdminBookings, AdminMessages, AdminPhotos, AdminServices,
} from "./admin-content";
import {
  AdminContentTab, AdminPayments, AdminSettings, AdminSecurity,
} from "./admin-settings";
import { AdminPlans, AdminRequests, AdminSubscribers } from "./admin-subs";
import { AdminSupport } from "./admin-support";
import { AdminVoices } from "./admin-voices";

type Me = { authenticated: boolean; email?: string; usingDefaultPassword?: boolean };

type TabKey =
  | "overview" | "plans" | "subscribers" | "requests" | "bookings" | "messages" | "support" | "voices" | "photos" | "services"
  | "content" | "payments" | "settings" | "security";

const TABS: { key: TabKey; label: string; icon: typeof LayoutDashboard }[] = [
  { key: "overview", label: "Overview", icon: LayoutDashboard },
  { key: "plans", label: "Plans", icon: Clapperboard },
  { key: "subscribers", label: "Subscribers", icon: Users },
  { key: "requests", label: "Video Queue", icon: Film },
  { key: "bookings", label: "Bookings", icon: CalendarCheck },
  { key: "messages", label: "Messages", icon: Mail },
  { key: "support", label: "Live Support", icon: RadioTower },
  { key: "voices", label: "Voice Licenses", icon: Mic },
  { key: "photos", label: "Photos", icon: ImageIcon },
  { key: "services", label: "Services", icon: Camera },
  { key: "content", label: "Reviews & FAQ", icon: MessageSquareQuote },
  { key: "payments", label: "Payments", icon: Wallet },
  { key: "settings", label: "Site & Profile", icon: SettingsIcon },
  { key: "security", label: "Security", icon: Lock },
];

export function AdminApp() {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<TabKey>("overview");
  const [defaultPwWarn, setDefaultPwWarn] = useState(false);

  const check = useCallback(async () => {
    try {
      const r = await api<Me>("/api/auth/me");
      setMe(r);
      if (r.usingDefaultPassword) setDefaultPwWarn(true);
    } catch {
      setMe({ authenticated: false });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    check();
  }, [check]);

  if (loading) {
    return (
      <section className="py-24 bg-[#F7F7F7] min-h-[70vh] flex items-center justify-center">
        <p className="text-muted-foreground font-semibold">Checking your session…</p>
      </section>
    );
  }

  if (!me?.authenticated) {
    return <LoginForm onDone={() => check()} />;
  }

  return (
    <section className="bg-[#F7F7F7] min-h-[80vh]">
      {defaultPwWarn && (
        <div className="bg-[var(--brand-red-dark)] text-white">
          <div className="mx-auto max-w-6xl px-4 py-3 flex items-center gap-3 text-sm font-semibold">
            <ShieldAlert className="h-5 w-5 shrink-0" aria-hidden />
            You are still using the default password. Change it now in{" "}
            <button onClick={() => setTab("security")} className="underline underline-offset-4 font-black">
              Security
            </button>
            .
            <button
              className="ml-auto text-white/80 hover:text-white"
              onClick={() => setDefaultPwWarn(false)}
              aria-label="Dismiss warning"
            >
              <X className="h-4 w-4" aria-hidden />
            </button>
          </div>
        </div>
      )}

      <div className="mx-auto max-w-6xl px-4 py-8">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.3em] text-primary">Owner area</p>
            <h1 className="text-3xl font-black tracking-tight uppercase">Admin Panel</h1>
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden sm:inline text-sm text-muted-foreground">{me.email}</span>
            <Button
              variant="outline"
              onClick={async () => {
                await api("/api/auth/logout", { method: "POST" });
                toast.success("Logged out");
                go("#");
              }}
            >
              <LogOut className="h-4 w-4" aria-hidden /> Log out
            </Button>
          </div>
        </div>

        <nav aria-label="Admin sections" className="mt-6 flex gap-2 overflow-x-auto dy-scroll-x pb-2">
          {TABS.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              aria-current={tab === key ? "page" : undefined}
              className={`inline-flex items-center gap-2 whitespace-nowrap px-4 py-2 text-sm font-bold border-2 transition-colors ${
                tab === key
                  ? "bg-[var(--brand-black)] text-white border-[var(--brand-black)]"
                  : "bg-white text-neutral-700 border-neutral-200 hover:border-primary hover:text-primary"
              }`}
            >
              <Icon className="h-4 w-4" aria-hidden /> {label}
            </button>
          ))}
        </nav>

        <div className="mt-6">
          {tab === "overview" && <Overview onNavigate={setTab} />}
          {tab === "plans" && <AdminPlans />}
          {tab === "subscribers" && <AdminSubscribers />}
          {tab === "requests" && <AdminRequests />}
          {tab === "bookings" && <AdminBookings />}
          {tab === "messages" && <AdminMessages />}
          {tab === "support" && <AdminSupport />}
          {tab === "voices" && <AdminVoices />}
          {tab === "photos" && <AdminPhotos />}
          {tab === "services" && <AdminServices />}
          {tab === "content" && <AdminContentTab />}
          {tab === "payments" && <AdminPayments />}
          {tab === "settings" && <AdminSettings />}
          {tab === "security" && <AdminSecurity onDone={() => setDefaultPwWarn(false)} />}
        </div>
      </div>
    </section>
  );
}

/* ---------------- Login ---------------- */

function LoginForm({ onDone }: { onDone: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
      toast.success("Welcome back, boss.");
      onDone();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="py-16 md:py-24 bg-[var(--brand-black)] min-h-[75vh] flex items-center">
      <div className="mx-auto max-w-md px-4 w-full">
        <div className="border-2 border-white/15 bg-white p-8 shadow-2xl">
          <div className="flex items-center gap-3">
            <span className="h-10 w-10 bg-primary flex items-center justify-center" aria-hidden>
              <Lock className="h-5 w-5 text-white" />
            </span>
            <div>
              <h1 className="text-2xl font-black uppercase tracking-tight">Owner Login</h1>
              <p className="text-xs text-muted-foreground">Only the site owner can enter here.</p>
            </div>
          </div>

          <form onSubmit={submit} className="mt-6 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="a-email">Email</Label>
              <Input
                id="a-email" type="email" required autoComplete="username"
                value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@deyoung.site"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="a-pass">Password</Label>
              <Input
                id="a-pass" type="password" required autoComplete="current-password"
                value={password} onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>
            <Button
              type="submit" disabled={busy}
              className="w-full h-11 bg-primary hover:bg-[#B91C1C] text-white font-bold"
            >
              {busy ? "Checking…" : "Enter Admin Panel"}
            </Button>
          </form>
          <p className="mt-4 text-xs text-muted-foreground text-center">
            First time? Log in with <strong>admin@deyoung.site</strong> / <strong>deyoung123</strong> - then
            change the password in Security immediately.
          </p>
        </div>
        <p className="mt-6 text-center">
          <a href="#" className="text-sm text-white/50 hover:text-primary font-semibold"><ArrowLeft className="h-4 w-4 inline align-[-2px]" aria-hidden /> Back to site</a>
        </p>
      </div>
    </section>
  );
}

/* ---------------- Overview ---------------- */

type OverviewData = {
  stats: {
    bookings: number; pending: number; paid: number; confirmed: number;
    revenueTotal: number; currency: string; messages: number; unread: number;
    photos: number; activeServices: number;
    subscribers: number; subscribersActive: number; subscribersPending: number;
    subsMrr: number; queueDepth: number; gpuMinutesToday: number; gpuMinutesBudget: number;
  };
  recentBookings: Booking[];
};

function Overview({ onNavigate }: { onNavigate: (t: TabKey) => void }) {
  const [data, setData] = useState<OverviewData | null>(null);

  useEffect(() => {
    api<OverviewData>("/api/overview").then(setData).catch(() => setData(null));
  }, []);

  if (!data) return <p className="text-muted-foreground p-6">Loading stats…</p>;
  const s = data.stats;

  const cards = [
    { label: "Monthly subscription revenue", value: money(s.subsMrr, s.currency), icon: Clapperboard, tab: "plans" as TabKey },
    { label: "Active subscribers", value: String(s.subscribersActive), icon: Users, tab: "subscribers" as TabKey },
    { label: "Videos in queue", value: String(s.queueDepth), icon: Film, tab: "requests" as TabKey },
    { label: "Revenue (paid + confirmed)", value: money(s.revenueTotal, s.currency), icon: BarChart3, tab: "bookings" as TabKey },
    { label: "Unread messages", value: String(s.unread), icon: Mail, tab: "messages" as TabKey },
    { label: "Live services", value: String(s.activeServices), icon: Sparkles, tab: "services" as TabKey },
  ];

  const gpuPct = Math.min(100, Math.round((s.gpuMinutesToday / Math.max(1, s.gpuMinutesBudget)) * 100));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        {cards.map(({ label, value, icon: Icon, tab: t }) => (
          <button
            key={label}
            onClick={() => onNavigate(t)}
            className="bg-white border-2 border-neutral-200 hover:border-primary transition-colors p-5 text-left"
          >
            <Icon className="h-5 w-5 text-primary" aria-hidden />
            <p className="mt-3 text-3xl font-black tracking-tight">{value}</p>
            <p className="text-xs font-semibold text-muted-foreground mt-1">{label}</p>
          </button>
        ))}
      </div>

      <div className="bg-white border-2 border-neutral-200 p-5">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="font-black uppercase tracking-tight">Today&apos;s render capacity</h2>
          <p className="text-sm text-muted-foreground font-semibold">
            {s.gpuMinutesToday} / {s.gpuMinutesBudget} GPU-minutes used
          </p>
        </div>
        <div className="mt-3 h-4 bg-neutral-100 border border-neutral-200" role="progressbar" aria-valuenow={gpuPct} aria-valuemin={0} aria-valuemax={100} aria-label="GPU minutes used today">
          <div className={`h-full ${gpuPct >= 90 ? "bg-primary" : "bg-[var(--brand-black)]"}`} style={{ width: `${gpuPct}%` }} />
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          Honest budget from your free GPU supply. When the bar is full, new requests simply join tomorrow&apos;s queue - never oversell.
          Adjust the daily budget in the database config or keep it as-is.
        </p>
      </div>

      <div className="bg-white border-2 border-neutral-200">
        <div className="px-5 py-4 border-b-2 border-neutral-100 flex items-center justify-between">
          <h2 className="font-black uppercase tracking-tight">Latest bookings</h2>
          <Button variant="ghost" size="sm" onClick={() => onNavigate("bookings")}>View all</Button>
        </div>
        {data.recentBookings.length === 0 ? (
          <p className="p-5 text-sm text-muted-foreground">No bookings yet - share your site link to get the first one.</p>
        ) : (
          <ul className="divide-y">
            {data.recentBookings.map((b) => (
              <li key={b.id} className="px-5 py-3 flex items-center gap-3 flex-wrap text-sm">
                <StatusBadge status={b.status} />
                <span className="font-bold">{b.name}</span>
                <span className="text-muted-foreground">{b.serviceTitle}</span>
                <span className="ml-auto font-black">{money(b.amount, b.currency)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: "bg-neutral-200 text-neutral-700",
    paid: "bg-primary text-white",
    confirmed: "bg-[var(--brand-black)] text-white",
    cancelled: "bg-neutral-100 text-neutral-400 line-through",
  };
  return (
    <span className={`text-[11px] font-black uppercase px-2.5 py-1 ${styles[status] ?? styles.pending}`}>
      {status}
    </span>
  );
}
