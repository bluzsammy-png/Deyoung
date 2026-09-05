import { guardAdmin, ok } from "@/lib/api";
import { getSettings } from "@/lib/settings";

/** Admin-only: full settings including hero/about fields (secret key never leaves the server). */
export async function GET() {
  const denied = await guardAdmin();
  if (denied) return denied;
  const s = await getSettings();
  const { paymentSecretKey: _secret, ...rest } = s;
  return ok({ settings: rest });
}
