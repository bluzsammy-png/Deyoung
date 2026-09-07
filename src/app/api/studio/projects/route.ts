import { db } from "@/lib/db";
import { bad, ok, str } from "@/lib/api";
import { getUserSession } from "@/lib/users";
import { guard } from "@/lib/ratelimit";

/** W2: list the signed-in user's studio projects (dashboard + studio restore). */
export async function GET() {
  const s = await getUserSession();
  if (s.kind === "anon") return bad("Sign in required", 401);
  if (s.kind === "blocked") return bad(`Account ${s.status}: ${s.reason}`, 403);
  const projects = await db.studioProject.findMany({
    where: { userId: s.user.id },
    orderBy: { updatedAt: "desc" },
    take: 30,
  });
  return ok({ projects });
}

/** W2: save (create or update) a studio project — brief, niche, generated script. */
export async function POST(req: Request) {
  const limited = await guard(req, "submit");
  if (limited) return limited;
  const s = await getUserSession();
  if (s.kind === "anon") return bad("Sign in required", 401);
  if (s.kind === "blocked") return bad(`Account ${s.status}: ${s.reason}`, 403);
  try {
    const body = await req.json().catch(() => ({}));
    const id = str(body.id, 40);
    const title = str(body.title, 120) || "Untitled film";
    const niche = str(body.niche, 60);
    const brief = str(body.brief, 4000);
    const scriptJson = str(body.scriptJson, 40000) || "{}";
    const status = ["draft", "scripted", "rendering", "done"].includes(str(body.status, 20))
      ? str(body.status, 20)
      : "draft";

    if (id) {
      const existing = await db.studioProject.findFirst({ where: { id, userId: s.user.id } });
      if (!existing) return bad("Project not found", 404);
      const updated = await db.studioProject.update({
        where: { id: existing.id },
        data: { title, niche, brief, scriptJson, status },
      });
      return ok({ project: updated });
    }
    const created = await db.studioProject.create({
      data: { userId: s.user.id, title, niche, brief, scriptJson, status },
    });
    return ok({ project: created }, 201);
  } catch (e) {
    console.error("studio project save failed", e);
    return bad("Could not save the project", 500);
  }
}
