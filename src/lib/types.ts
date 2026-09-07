export type PublicSettings = {
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
  paymentProvider: "manual" | "paystack" | "flutterwave" | "paypal" | "stripe" | string;
  // Public-by-design payment fields: the Paystack/Flutterwave/PayPal PUBLIC key
  // is required client-side by their SDKs, and paymentLinkUrl is a
  // customer-facing checkout link. The SECRET key is never exposed here.
  paymentPublicKey: string;
  paymentLinkUrl: string;
  paymentInstructions: string;
  bankDetails: string;
  socialJson: string;
  metaDescription: string;
};

export type Service = {
  id: string;
  title: string;
  description: string;
  price: number;
  compareAtPrice?: number | null;
  duration: string;
  active: boolean;
  sortOrder: number;
};

export type Photo = {
  id: string;
  title: string;
  alt: string;
  url: string;
  category?: string; // work | ai-film | style-lab
  sortOrder: number;
  createdAt?: string;
};

export type Testimonial = {
  id: string;
  name: string;
  role: string;
  quote: string;
  rating: number;
  active: boolean;
  sortOrder: number;
};

export type Faq = {
  id: string;
  question: string;
  answer: string;
  sortOrder: number;
  active: boolean;
};

export type Booking = {
  id: string;
  name: string;
  email: string;
  phone: string;
  serviceTitle: string;
  amount: number;
  currency: string;
  status: "pending" | "paid" | "confirmed" | "cancelled" | string;
  provider: string;
  paymentRef: string;
  notes: string;
  createdAt: string;
  updatedAt: string;
};

export type Message = {
  id: string;
  name: string;
  email: string;
  body: string;
  read: boolean;
  createdAt: string;
};

export type HomeData = {
  settings: PublicSettings;
  services: Service[];
  photos: Photo[];
  testimonials: Testimonial[];
  faqs: Faq[];
  plans: Plan[];
};

export type PlanFeature = { label: string; included: boolean };

export type Plan = {
  id: string;
  code: string;
  name: string;
  blurb: string;
  priceMonthly: number;
  compareAtPrice?: number | null;
  currency: string;
  maxVideosMonth: number;
  maxSecondsVideo: number;
  maxResolution: string;
  watermark: boolean;
  concurrentJobs: number;
  queuePriority: number;
  commercial: boolean;
  audio: boolean;
  featuresJson: string;
  active: boolean;
  sortOrder: number;
};

export type Subscription = {
  id: string;
  name: string;
  email: string;
  phone: string;
  planCode: string;
  status: "pending" | "active" | "expired" | "cancelled" | string;
  periodStart?: string | null;
  periodEnd?: string | null;
  pricePaid: number;
  currency: string;
  provider: string;
  paymentRef: string;
  notes: string;
  createdAt: string;
  updatedAt: string;
};

export type VideoRequest = {
  id: string;
  subscriptionId: string;
  email: string;
  prompt: string;
  seconds: number;
  resolution: string;
  withAudio: boolean;
  watermark: boolean;
  queuePriority: number;
  status: "queued" | "rendering" | "done" | "failed" | "cancelled" | string;
  resultUrl: string;
  gpuMinutes: number;
  fromCache: boolean;
  notes: string;
  createdAt: string;
  updatedAt: string;
};

export function money(amount: number, currency: string): string {
  const symbols: Record<string, string> = {
    USD: "$",
    EUR: "\u20AC",
    GBP: "\u00A3",
    NGN: "\u20A6",
    GHS: "GH\u20B5",
    KES: "KSh ",
    ZAR: "R",
    XOF: "CFA ",
    CAD: "C$",
  };
  const s = symbols[currency] ?? `${currency} `;
  const n = Number.isInteger(amount) ? String(amount) : amount.toFixed(2);
  return `${s}${n}`;
}

export async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...init,
    headers:
      init?.body && !(init.body instanceof FormData)
        ? { "Content-Type": "application/json", ...init?.headers }
        : init?.headers,
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((json as { error?: string }).error || "Something went wrong");
  return json as T;
}
