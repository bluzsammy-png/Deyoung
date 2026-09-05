import { db } from "@/lib/db";
import { bad, guardAdmin, ok, str } from "@/lib/api";
import { getSettings, publicSettings } from "@/lib/settings";

export async function GET() {
  const s = await getSettings();
  return ok({ settings: publicSettings(s) });
}

const TEXT_FIELDS = [
  "siteName",
  "tagline",
  "heroTitle",
  "heroSubtitle",
  "aboutTitle",
  "aboutBody",
  "ownerName",
  "ownerTitle",
  "ownerPhotoUrl",
  "contactEmail",
  "phone",
  "whatsapp",
  "location",
  "responseTime",
  "currency",
  "paymentProvider",
  "paymentPublicKey",
  "paymentSecretKey",
  "paymentLinkUrl",
  "paymentInstructions",
  "bankDetails",
  "socialJson",
  "metaDescription",
] as const;

export async function PUT(req: Request) {
  const denied = await guardAdmin();
  if (denied) return denied;

  const body = await req.json().catch(() => ({}));
  if (typeof body.socialJson === "string") {
    try {
      JSON.parse(body.socialJson);
    } catch {
      return bad("socialJson must be valid JSON");
    }
  }
  const provider = str(body.paymentProvider, 30) || "manual";
  if (!["manual", "paystack", "flutterwave", "paypal", "stripe"].includes(provider)) {
    return bad("Unknown payment provider");
  }

  const data: Record<string, string> = { paymentProvider: provider };
  for (const f of TEXT_FIELDS) {
    if (f in body) data[f] = str(body[f], 8000);
  }
  await getSettings();
  const updated = await db.settings.update({ where: { id: "main" }, data });
  return ok({ settings: publicSettings(updated) });
}
