import "server-only";
import { db } from "@/lib/db";

export type SiteSettings = {
  siteName: string;
  tagline: string;
  heroTitle: string;
  heroSubtitle: string;
  aboutTitle: string;
  aboutBody: string;
  ownerName: string;
  ownerTitle: string;
  ownerPhotoUrl: string;
  contactEmail: string;
  phone: string;
  whatsapp: string;
  location: string;
  responseTime: string;
  currency: string;
  paymentProvider: string;
  paymentPublicKey: string;
  paymentSecretKey: string;
  paymentLinkUrl: string;
  paymentInstructions: string;
  bankDetails: string;
  socialJson: string;
  metaDescription: string;
};

/** Public-safe fields (no payment keys) - used by the public site. */
export function publicSettings(s: SiteSettings) {
  return {
    siteName: s.siteName,
    tagline: s.tagline,
    heroTitle: s.heroTitle,
    heroSubtitle: s.heroSubtitle,
    aboutTitle: s.aboutTitle,
    aboutBody: s.aboutBody,
    ownerName: s.ownerName,
    ownerTitle: s.ownerTitle,
    ownerPhotoUrl: s.ownerPhotoUrl,
    contactEmail: s.contactEmail,
    phone: s.phone,
    whatsapp: s.whatsapp,
    location: s.location,
    responseTime: s.responseTime,
    currency: s.currency,
    paymentProvider: s.paymentProvider,
    paymentInstructions: s.paymentInstructions,
    bankDetails: s.bankDetails,
    socialJson: s.socialJson,
    metaDescription: s.metaDescription,
  };
}

export async function getSettings() {
  const existing = await db.settings.findUnique({ where: { id: "main" } });
  if (existing) return existing;
  return db.settings.create({
    data: {
      id: "main",
      aboutBody:
        "I'm DeYoung - a creative professional who keeps things simple: sharp work, honest pricing and fast delivery. Everything you see here is work I actually did for real people. Book a service, tell me what you need, and consider it handled.",
    },
  });
}
