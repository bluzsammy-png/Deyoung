import { db } from "@/lib/db";
import { guardAdmin, ok } from "@/lib/api";

export async function GET() {
  const denied = await guardAdmin();
  if (denied) return denied;
  const messages = await db.message.findMany({ orderBy: { createdAt: "desc" } });
  return ok({ messages });
}
