import { db } from "@/lib/db";
import { ok } from "@/lib/api";
import { getSettings, publicSettings } from "@/lib/settings";

/** One call powering the whole public site. */
export async function GET() {
  const [settings, services, photos, testimonials, faqs, plans] = await Promise.all([
    getSettings(),
    db.service.findMany({ where: { active: true }, orderBy: { sortOrder: "asc" } }),
    db.photo.findMany({ orderBy: { sortOrder: "asc" } }),
    db.testimonial.findMany({ where: { active: true }, orderBy: { sortOrder: "asc" } }),
    db.faq.findMany({ where: { active: true }, orderBy: { sortOrder: "asc" } }),
    db.plan.findMany({ where: { active: true }, orderBy: { sortOrder: "asc" } }),
  ]);
  return ok({ settings: publicSettings(settings), services, photos, testimonials, faqs, plans });
}
