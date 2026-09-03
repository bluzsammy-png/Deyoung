import "server-only";
import { NextResponse } from "next/server";
import { isAdmin } from "@/lib/auth";

export function ok(data: unknown, init?: number) {
  return NextResponse.json(data as object, { status: init ?? 200 });
}

export function bad(message: string, status = 400) {
  return NextResponse.json({ error: message }, { status });
}

/** Returns a 401 response when the caller is not the owner, otherwise null. */
export async function guardAdmin(): Promise<NextResponse | null> {
  if (await isAdmin()) return null;
  return bad("Owner access only", 401);
}

export function str(v: unknown, max = 5000): string {
  return typeof v === "string" ? v.trim().slice(0, max) : "";
}

export function num(v: unknown): number {
  const n = typeof v === "number" ? v : parseFloat(String(v));
  return Number.isFinite(n) ? n : 0;
}
