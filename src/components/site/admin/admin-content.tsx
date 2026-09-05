"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Image from "next/image";
import { Check, Loader2, Mail, MailOpen, Pencil, Plus, Trash2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { api, money, type Booking, type Message, type Photo, type Service } from "@/lib/types";
import { StatusBadge } from "./admin-app";

export function AdminPanel({ title, children, action }: { title: string; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="bg-white border-2 border-neutral-200">
      <div className="px-5 py-4 border-b-2 border-neutral-100 flex items-center justify-between gap-3 flex-wrap">
        <h2 className="font-black uppercase tracking-tight">{title}</h2>
        {action}
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

/* ---------------- Bookings (= your customers/users) ---------------- */

export function AdminBookings() {
  const [bookings, setBookings] = useState<Booking[] | null>(null);

  const load = useCallback(() => {
    api<{ bookings: Booking[] }>("/api/bookings").then((r) => setBookings(r.bookings)).catch(() => setBookings([]));
  }, []);

  useEffect(load, [load]);

  async function setStatus(id: string, status: string) {
    try {
      await api(`/api/bookings/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      toast.success(`Marked as ${status}`);
      load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Update failed");
    }
  }

  async function remove(id: string) {
    if (!confirm("Delete this booking? This cannot be undone.")) return;
    await api(`/api/bookings/${id}`, { method: "DELETE" }).catch(() => null);
    toast.success("Booking deleted");
    load();
  }

  if (!bookings) return <p className="text-muted-foreground">Loading bookings…</p>;

  return (
    <AdminPanel title={`Bookings & customers (${bookings.length})`}>
      {bookings.length === 0 ? (
        <p className="text-sm text-muted-foreground">No bookings yet. When someone books, they appear here.</p>
      ) : (
        <ul className="divide-y">
          {bookings.map((b) => (
            <li key={b.id} className="py-4 grid gap-3 md:grid-cols-[auto_1fr_auto] items-start">
              <StatusBadge status={b.status} />
              <div className="text-sm">
                <p className="font-bold">
                  {b.name}{" "}
                  <a href={`mailto:${b.email}`} className="font-normal text-primary underline underline-offset-2">{b.email}</a>
                  {b.phone ? <span className="font-normal text-muted-foreground"> · {b.phone}</span> : null}
                </p>
                <p className="text-muted-foreground">
                  {b.serviceTitle} · {new Date(b.createdAt).toLocaleString()}
                </p>
                {b.notes ? <p className="mt-1 text-neutral-600">&ldquo;{b.notes}&rdquo;</p> : null}
                {b.paymentRef ? <p className="mt-1 text-xs text-muted-foreground">Ref: {b.paymentRef}</p> : null}
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-black mr-2">{money(b.amount, b.currency)}</span>
                <select
                  aria-label={`Status for booking by ${b.name}`}
                  value={b.status}
                  onChange={(e) => setStatus(b.id, e.target.value)}
                  className="h-9 rounded-md border border-input bg-background px-2 text-sm"
                >
                  <option value="pending">pending</option>
                  <option value="paid">paid</option>
                  <option value="confirmed">confirmed</option>
                  <option value="cancelled">cancelled</option>
                </select>
                <Button variant="ghost" size="icon" aria-label={`Delete booking by ${b.name}`} onClick={() => remove(b.id)}>
                  <Trash2 className="h-4 w-4 text-neutral-400 hover:text-destructive" />
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </AdminPanel>
  );
}

/* ---------------- Messages ---------------- */

export function AdminMessages() {
  const [messages, setMessages] = useState<Message[] | null>(null);

  const load = useCallback(() => {
    api<{ messages: Message[] }>("/api/messages").then((r) => setMessages(r.messages)).catch(() => setMessages([]));
  }, []);

  useEffect(load, [load]);

  if (!messages) return <p className="text-muted-foreground">Loading messages…</p>;

  return (
    <AdminPanel title={`Inbox (${messages.filter((m) => !m.read).length} unread)`}>
      {messages.length === 0 ? (
        <p className="text-sm text-muted-foreground">No messages yet.</p>
      ) : (
        <ul className="space-y-3">
          {messages.map((m) => (
            <li key={m.id} className={`border-2 p-4 ${m.read ? "border-neutral-100" : "border-primary/40 bg-[#FFF8F8]"}`}>
              <div className="flex items-center gap-2 flex-wrap text-sm">
                {m.read ? <MailOpen className="h-4 w-4 text-neutral-300" aria-hidden /> : <Mail className="h-4 w-4 text-primary" aria-hidden />}
                <span className="font-bold">{m.name}</span>
                <a href={`mailto:${m.email}`} className="text-primary underline underline-offset-2">{m.email}</a>
                <span className="ml-auto text-xs text-muted-foreground">{new Date(m.createdAt).toLocaleString()}</span>
              </div>
              <p className="mt-2 text-sm text-neutral-700 whitespace-pre-line">{m.body}</p>
              <div className="mt-3 flex gap-2">
                {!m.read && (
                  <Button size="sm" variant="outline" onClick={async () => { await api(`/api/messages/${m.id}`, { method: "PATCH" }); load(); }}>
                    <MailOpen className="h-3.5 w-3.5" aria-hidden /> Mark read
                  </Button>
                )}
                <Button size="sm" variant="ghost" onClick={async () => { if (!confirm("Delete message?")) return; await api(`/api/messages/${m.id}`, { method: "DELETE" }); load(); }}>
                  <Trash2 className="h-3.5 w-3.5" aria-hidden /> Delete
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </AdminPanel>
  );
}

/* ---------------- Photos ---------------- */

export function AdminPhotos() {
  const [photos, setPhotos] = useState<Photo[] | null>(null);
  const [uploading, setUploading] = useState(false);
  const [editing, setEditing] = useState<Photo | null>(null);
  const [adding, setAdding] = useState(false);
  const [newPhoto, setNewPhoto] = useState({ title: "", alt: "", url: "" });
  const fileRef = useRef<HTMLInputElement>(null);
  const addFileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(() => {
    api<{ photos: Photo[] }>("/api/photos").then((r) => setPhotos(r.photos)).catch(() => setPhotos([]));
  }, []);

  useEffect(load, [load]);

  async function uploadFile(file: File, onUrl: (url: string) => void) {
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await api<{ url: string }>("/api/upload", { method: "POST", body: fd });
      onUrl(res.url);
      toast.success("Image uploaded");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function addPhoto() {
    if (!newPhoto.url || !newPhoto.title) return toast.error("Pick an image and give it a title");
    await api("/api/photos", { method: "POST", body: JSON.stringify(newPhoto) });
    toast.success("Photo added to gallery");
    setNewPhoto({ title: "", alt: "", url: "" });
    setAdding(false);
    load();
  }

  async function saveEdit() {
    if (!editing) return;
    await api(`/api/photos/${editing.id}`, {
      method: "PATCH",
      body: JSON.stringify({ title: editing.title, alt: editing.alt, sortOrder: editing.sortOrder }),
    });
    toast.success("Photo updated");
    setEditing(null);
    load();
  }

  async function remove(id: string) {
    if (!confirm("Remove this photo from the gallery?")) return;
    await api(`/api/photos/${id}`, { method: "DELETE" }).catch(() => null);
    load();
  }

  if (!photos) return <p className="text-muted-foreground">Loading photos…</p>;

  return (
    <AdminPanel
      title={`Gallery (${photos.length} photos)`}
      action={
        <Button size="sm" onClick={() => setAdding(true)} className="bg-primary hover:bg-[#B91C1C] text-white font-bold">
          <Plus className="h-4 w-4" aria-hidden /> Add photo
        </Button>
      }
    >
      {photos.length === 0 ? (
        <p className="text-sm text-muted-foreground">Gallery is empty - add your first photo.</p>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {photos.map((p) => (
            <figure key={p.id} className="border-2 border-neutral-200 group">
              <div className="relative aspect-[4/3] bg-neutral-100">
                <Image src={p.url} alt={p.alt || p.title} fill sizes="33vw" className="object-cover" />
              </div>
              <figcaption className="p-3">
                <p className="font-bold text-sm truncate">{p.title}</p>
                <div className="mt-2 flex gap-1">
                  <Button size="icon" variant="ghost" aria-label={`Edit ${p.title}`} onClick={() => setEditing(p)}>
                    <Pencil className="h-4 w-4 text-neutral-500" />
                  </Button>
                  <Button size="icon" variant="ghost" aria-label={`Delete ${p.title}`} onClick={() => remove(p.id)}>
                    <Trash2 className="h-4 w-4 text-neutral-400 hover:text-destructive" />
                  </Button>
                </div>
              </figcaption>
            </figure>
          ))}
        </div>
      )}

      {/* Add dialog */}
      <Dialog open={adding} onOpenChange={setAdding}>
        <DialogContent aria-describedby={undefined}>
          <DialogHeader>
            <DialogTitle className="uppercase font-black">Add photo</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Image file</Label>
              <input
                ref={addFileRef} type="file" accept="image/*" className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) uploadFile(f, (url) => setNewPhoto((p) => ({ ...p, url })));
                }}
              />
              <Button variant="outline" onClick={() => addFileRef.current?.click()} disabled={uploading} className="w-full">
                {uploading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Upload className="h-4 w-4" aria-hidden />}
                {newPhoto.url ? "Replace image" : "Choose image (max 8MB)"}
              </Button>
              {newPhoto.url ? (
                <div className="relative aspect-video mt-2 bg-neutral-100">
                  <Image src={newPhoto.url} alt="Selected upload preview" fill sizes="100vw" className="object-contain" />
                </div>
              ) : null}
            </div>
            <div className="space-y-2">
              <Label htmlFor="np-title">Title</Label>
              <Input id="np-title" value={newPhoto.title} onChange={(e) => setNewPhoto({ ...newPhoto, title: e.target.value })} placeholder="e.g. Portrait session - Amara" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="np-alt">Alt text (for accessibility & SEO)</Label>
              <Input id="np-alt" value={newPhoto.alt} onChange={(e) => setNewPhoto({ ...newPhoto, alt: e.target.value })} placeholder="Describe the photo" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAdding(false)}>Cancel</Button>
            <Button onClick={addPhoto} className="bg-primary hover:bg-[#B91C1C] text-white font-bold"><Check className="h-4 w-4" aria-hidden /> Add to gallery</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit dialog */}
      <Dialog open={!!editing} onOpenChange={(v) => !v && setEditing(null)}>
        <DialogContent aria-describedby={undefined}>
          <DialogHeader>
            <DialogTitle className="uppercase font-black">Edit photo</DialogTitle>
          </DialogHeader>
          {editing && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="ep-title">Title</Label>
                <Input id="ep-title" value={editing.title} onChange={(e) => setEditing({ ...editing, title: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ep-alt">Alt text</Label>
                <Input id="ep-alt" value={editing.alt} onChange={(e) => setEditing({ ...editing, alt: e.target.value })} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ep-order">Sort order</Label>
                <Input id="ep-order" type="number" value={editing.sortOrder} onChange={(e) => setEditing({ ...editing, sortOrder: parseInt(e.target.value, 10) || 0 })} />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditing(null)}>Cancel</Button>
            <Button onClick={saveEdit} className="bg-primary hover:bg-[#B91C1C] text-white font-bold"><Check className="h-4 w-4" aria-hidden /> Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminPanel>
  );
}

/* ---------------- Services ---------------- */

type ServiceDraft = { title: string; description: string; price: number; duration: string; active: boolean };

const EMPTY_DRAFT: ServiceDraft = { title: "", description: "", price: 0, duration: "", active: true };

export function AdminServices() {
  const [services, setServices] = useState<Service[] | null>(null);
  const [editing, setEditing] = useState<Service | null>(null);
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState<ServiceDraft>(EMPTY_DRAFT);

  const load = useCallback(() => {
    api<{ services: Service[] }>("/api/services").then((r) => setServices(r.services)).catch(() => setServices([]));
  }, []);

  useEffect(load, [load]);

  async function addService() {
    if (!draft.title.trim()) return toast.error("Title is required");
    await api("/api/services", { method: "POST", body: JSON.stringify(draft) });
    toast.success("Service added");
    setDraft(EMPTY_DRAFT);
    setAdding(false);
    load();
  }

  async function saveEdit() {
    if (!editing) return;
    await api(`/api/services/${editing.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        title: editing.title, description: editing.description,
        price: editing.price, duration: editing.duration, active: editing.active,
      }),
    });
    toast.success("Service updated");
    setEditing(null);
    load();
  }

  async function remove(id: string) {
    if (!confirm("Delete this service?")) return;
    await api(`/api/services/${id}`, { method: "DELETE" }).catch(() => null);
    load();
  }

  if (!services) return <p className="text-muted-foreground">Loading services…</p>;

  return (
    <AdminPanel
      title={`Services (${services.length})`}
      action={
        <Button size="sm" onClick={() => setAdding(true)} className="bg-primary hover:bg-[#B91C1C] text-white font-bold">
          <Plus className="h-4 w-4" aria-hidden /> Add service
        </Button>
      }
    >
      <ul className="divide-y">
        {services.map((s) => (
          <li key={s.id} className="py-4 flex items-start gap-4 flex-wrap">
            <div className="flex-1 min-w-52">
              <p className="font-bold flex items-center gap-2">
                {s.title}
                {!s.active && <span className="text-[10px] font-black uppercase bg-neutral-200 text-neutral-500 px-2 py-0.5">hidden</span>}
              </p>
              <p className="text-sm text-muted-foreground line-clamp-2">{s.description}</p>
              {s.duration ? <p className="text-xs text-neutral-500 mt-0.5">{s.duration}</p> : null}
            </div>
            <p className="font-black">{money(s.price, "USD")}</p>
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2">
                <Switch
                  checked={s.active}
                  onCheckedChange={(v) =>
                    api(`/api/services/${s.id}`, { method: "PATCH", body: JSON.stringify({ active: v }) }).then(load)
                  }
                  aria-label={`Show ${s.title} on site`}
                />
                <span className="text-xs text-muted-foreground">live</span>
              </div>
              <Button size="icon" variant="ghost" aria-label={`Edit ${s.title}`} onClick={() => setEditing(s)}>
                <Pencil className="h-4 w-4 text-neutral-500" />
              </Button>
              <Button size="icon" variant="ghost" aria-label={`Delete ${s.title}`} onClick={() => remove(s.id)}>
                <Trash2 className="h-4 w-4 text-neutral-400 hover:text-destructive" />
              </Button>
            </div>
          </li>
        ))}
      </ul>

      {/* Add dialog */}
      <Dialog open={adding} onOpenChange={setAdding}>
        <DialogContent aria-describedby={undefined}>
          <DialogHeader><DialogTitle className="uppercase font-black">Add service</DialogTitle></DialogHeader>
          <ServiceFields draft={draft} setDraft={setDraft} />
          <DialogFooter>
            <Button variant="outline" onClick={() => setAdding(false)}>Cancel</Button>
            <Button onClick={addService} className="bg-primary hover:bg-[#B91C1C] text-white font-bold"><Check className="h-4 w-4" aria-hidden /> Add</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit dialog */}
      <Dialog open={!!editing} onOpenChange={(v) => !v && setEditing(null)}>
        <DialogContent aria-describedby={undefined}>
          <DialogHeader><DialogTitle className="uppercase font-black">Edit service</DialogTitle></DialogHeader>
          {editing && (
            <ServiceFields
              draft={{
                title: editing.title, description: editing.description,
                price: editing.price, duration: editing.duration, active: editing.active,
              }}
              setDraft={(d) => setEditing({ ...editing, ...d })}
            />
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditing(null)}>Cancel</Button>
            <Button onClick={saveEdit} className="bg-primary hover:bg-[#B91C1C] text-white font-bold"><Check className="h-4 w-4" aria-hidden /> Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminPanel>
  );
}

function ServiceFields({ draft, setDraft }: { draft: ServiceDraft; setDraft: (d: ServiceDraft) => void }) {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="sv-title">Title</Label>
        <Input id="sv-title" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} placeholder="e.g. Portrait Session" />
      </div>
      <div className="space-y-2">
        <Label htmlFor="sv-desc">Description</Label>
        <Textarea id="sv-desc" rows={3} value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} placeholder="What the client gets…" />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="sv-price">Price</Label>
          <Input id="sv-price" type="number" min="0" step="0.01" value={draft.price} onChange={(e) => setDraft({ ...draft, price: parseFloat(e.target.value) || 0 })} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="sv-dur">Duration</Label>
          <Input id="sv-dur" value={draft.duration} onChange={(e) => setDraft({ ...draft, duration: e.target.value })} placeholder="e.g. 2 hours" />
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Switch checked={draft.active} onCheckedChange={(v) => setDraft({ ...draft, active: v })} id="sv-active" />
        <Label htmlFor="sv-active">Show on site</Label>
      </div>
    </div>
  );
}
