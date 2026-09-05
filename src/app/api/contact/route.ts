import { db } from "@/lib/db";
import { bad, ok, str } from "@/lib/api";
import { sendOwnerEmail } from "@/lib/agentmail";

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const name = str(body.name, 120);
  const email = str(body.email, 200);
  const message = str(body.body, 4000);
  if (!name || !email || !message) return bad("Name, email and message are required");
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return bad("Please enter a valid email");

  await db.message.create({ data: { name, email, body: message } });

  // Notify the owner's AgentMail inbox (non-fatal: DB row is already saved).
  void sendOwnerEmail({
    subject: `New website message - ${name}`,
    replyTo: email,
    text: [
      `You have a new message from the website contact form.`,
      ``,
      `Name:    ${name}`,
      `Email:   ${email}`,
      ``,
      `Message:`,
      message,
      ``,
      `Reply directly to this email to answer ${name}.`,
    ].join("\n"),
  }).catch(() => {});

  return ok({ sent: true });
}
