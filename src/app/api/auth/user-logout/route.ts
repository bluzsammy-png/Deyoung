import { ok } from "@/lib/api";
import { destroyUserSession } from "@/lib/users";

/** W2: sign the site user out (admin session on dy_admin is untouched). */
export async function POST() {
  await destroyUserSession();
  return ok({ signedOut: true });
}
