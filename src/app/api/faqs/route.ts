import { db } from "@/lib/db";
import { bad, guardAdmin, ok, str } from "@/lib/api";

export async function GET() {
  const faqs = await db.faq.findMany({ orderBy: { sortOrder: "asc" } });
  return ok({ faqs });
}

export async function POST(req: Request) {
  const denied = await guardAdmin();
  if (denied) return denied;
  const body = await req.json().catch(() => ({}));
  const question = str(body.question, 300);
  const answer = str(body.answer, 3000);
  if (!question || !answer) return bad("Question and answer are required");
  const max = await db.faq.aggregate({ _max: { sortOrder: true } });
  const faq = await db.faq.create({
    data: { question, answer, sortOrder: (max._max.sortOrder ?? 0) + 1 },
  });
  return ok({ faq });
}
