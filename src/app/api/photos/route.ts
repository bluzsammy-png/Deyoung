import { db } from "@/lib/db";
import { bad, guardAdmin, ok, str } from "@/lib/api";

export async function GET() {
  const photos = await db.photo.findMany({ orderBy: { sortOrder: "asc" } });
  return ok({ photos });
}

export async function POST(req: Request) {
  const denied = await guardAdmin();
  if (denied) return denied;
  const body = await req.json().catch(() => ({}));
  const title = str(body.title, 160);
  const alt = str(body.alt, 300);
  const url = str(body.url, 500);
  if (!title || !url) return bad("Title and image are required");
  const photo = await db.photo.create({
    data: { title, alt: alt || title, url, sortOrder: num0(body.sortOrder) },
  });
  return ok({ photo });
}

function num0(v: unknown): number {
  const n = typeof v === "number" ? v : parseInt(String(v), 10);
  return Number.isFinite(n) ? n : 0;
}
