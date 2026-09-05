import { db } from "@/lib/db";
import { bad, guardAdmin, num, ok, str } from "@/lib/api";

export async function GET() {
  const services = await db.service.findMany({ orderBy: { sortOrder: "asc" } });
  return ok({ services });
}

export async function POST(req: Request) {
  const denied = await guardAdmin();
  if (denied) return denied;
  const body = await req.json().catch(() => ({}));
  const title = str(body.title, 160);
  const description = str(body.description, 2000);
  if (!title) return bad("Title is required");
  const max = await db.service.aggregate({ _max: { sortOrder: true } });
  const service = await db.service.create({
    data: {
      title,
      description,
      price: num(body.price),
      duration: str(body.duration, 80),
      active: body.active !== false,
      sortOrder: (max._max.sortOrder ?? 0) + 1,
    },
  });
  return ok({ service });
}
