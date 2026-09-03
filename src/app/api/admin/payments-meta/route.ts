import { db } from "@/lib/db";
import { guardAdmin, ok } from "@/lib/api";
import { getSettings } from "@/lib/settings";

/** Admin-only: whether a payment secret key exists (never returns the key itself). */
export async function GET() {
  const denied = await guardAdmin();
  if (denied) return denied;
  const s = await getSettings();
  return ok({
    hasSecret: s.paymentSecretKey.length > 0,
    secretPreview: "",
    provider: s.paymentProvider,
  });
}
