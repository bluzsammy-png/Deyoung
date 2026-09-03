import { db } from "@/lib/db";
import { bad, ok, str } from "@/lib/api";

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const name = str(body.name, 120);
  const email = str(body.email, 200);
  const message = str(body.body, 4000);
  if (!name || !email || !message) return bad("Name, email and message are required");
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return bad("Please enter a valid email");

  await db.message.create({ data: { name, email, body: message } });
  return ok({ sent: true });
}
