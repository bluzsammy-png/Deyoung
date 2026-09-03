import { db } from "@/lib/db";
import { bad, guardAdmin, ok, str } from "@/lib/api";

export async function GET() {
  const testimonials = await db.testimonial.findMany({ orderBy: { sortOrder: "asc" } });
  return ok({ testimonials });
}

export async function POST(req: Request) {
  const denied = await guardAdmin();
  if (denied) return denied;
  const body = await req.json().catch(() => ({}));
  const name = str(body.name, 120);
  const quote = str(body.quote, 1000);
  if (!name || !quote) return bad("Name and quote are required");
  const max = await db.testimonial.aggregate({ _max: { sortOrder: true } });
  const t = await db.testimonial.create({
    data: {
      name,
      role: str(body.role, 120),
      quote,
      rating: Math.min(5, Math.max(1, parseInt(String(body.rating ?? 5), 10) || 5)),
      sortOrder: (max._max.sortOrder ?? 0) + 1,
    },
  });
  return ok({ testimonial: t });
}
