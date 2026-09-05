import { ok } from "@/lib/api";
import { googleConfigured } from "@/lib/google";

export const dynamic = "force-dynamic";

/** GET /api/auth/google/status - tells the sign-in view whether Google is enabled. */
export async function GET() {
  return ok({ configured: googleConfigured() });
}
