"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { api, type HomeData } from "@/lib/types";
import { useHashRoute } from "@/components/site/hash";
import { SiteHeader } from "@/components/site/header";
import { Hero, StickyMobileCta } from "@/components/site/hero";
import {
  About, Contact, FaqSection, Gallery, HowItWorks, Services, SiteFooter, StatsStrip, Testimonials,
} from "@/components/site/sections";
import { BookView } from "@/components/site/book-view";
import { SubscribeView } from "@/components/site/subscribe-view";
import { RequestView } from "@/components/site/request-view";
import { PlansSection } from "@/components/site/plans";
import { Parade } from "@/components/site/parade";
import { CampaignStrip } from "@/components/site/campaign";
import { ThankYouView } from "@/components/site/thank-you-privacy";
import { LegalView } from "@/components/site/legal";
import { StudioView } from "@/components/site/studio";
import { AdminApp } from "@/components/site/admin/admin-app";

export default function Page() {
  const route = useHashRoute();
  const [data, setData] = useState<HomeData | null>(null);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    api<HomeData>("/api/home")
      .then(setData)
      .catch(() => setLoadError(true));
  }, []);

  if (loadError) {
    return (
      <div className="min-h-screen flex flex-col">
        <SiteHeader settings={null} />
        <main className="flex-1 flex items-center justify-center p-8">
          <div className="text-center max-w-md">
            <p className="text-5xl font-black uppercase text-primary">Oops.</p>
            <p className="mt-3 text-muted-foreground">
              The site could not load its content. Refresh the page - if it keeps failing, the owner has
              been notified already.
            </p>
            <Button onClick={() => window.location.reload()} className="mt-6 bg-primary hover:bg-[#B91C1C] text-white font-bold">
              Refresh
            </Button>
          </div>
        </main>
        <SiteFooter settings={null} />
      </div>
    );
  }

  const settings = data?.settings ?? null;
  const siteName = settings?.siteName || "DeYoung";

  /* ---------------- views ---------------- */

  let view: React.ReactNode;
  switch (route.name) {
    case "book":
      view = (
        <main className="flex-1">
          <BookView settings={settings} services={data?.services ?? []} preselect={route.serviceId} />
        </main>
      );
      break;
    case "subscribe":
      view = (
        <main className="flex-1">
          <SubscribeView
            settings={settings}
            plans={data?.plans ?? []}
            preselectPlan={route.planCode}
          />
        </main>
      );
      break;
    case "plans":
      view = (
        <main className="flex-1">
          <PlansSection plans={data?.plans ?? []} currency={settings?.currency || "USD"} standalone />
          <HowItWorks />
        </main>
      );
      break;
    case "request":
      view = (
        <main className="flex-1">
          <RequestView />
        </main>
      );
      break;
    case "studio":
      view = <StudioView />;
      break;
    case "legal":
      view = <LegalView initial={route.doc} />;
      break;
    case "thanks":
      view = (
        <main className="flex-1">
          <ThankYouView bookingId={route.bookingId} paid={route.paid} siteName={siteName} />
        </main>
      );
      break;
    case "admin":
      view = (
        <main className="flex-1">
          <AdminApp />
        </main>
      );
      break;
    default:
      view = (
        <main className="flex-1">
          <Hero settings={settings} />
          <Parade variant="a" />
          <StatsStrip />
          <CampaignStrip />
          <PlansSection plans={data?.plans ?? []} currency={settings?.currency || "USD"} />
          <HowItWorks />
          <Services services={data?.services ?? []} currency={settings?.currency || "USD"} />
          <Parade variant="b" />
          <Gallery photos={data?.photos ?? []} />
          <About settings={settings} />
          <Testimonials testimonials={data?.testimonials ?? []} />
          <FaqSection faqs={data?.faqs ?? []} />
          <Contact settings={settings} />
        </main>
      );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <SiteHeader settings={settings} />
      {view}
      {route.name === "home" && <StickyMobileCta whatsapp={settings?.whatsapp} />}
      <SiteFooter settings={settings} />
      <StructuredData siteName={siteName} settings={settings} />
    </div>
  );
}

/* ---------------- JSON-LD ---------------- */

function StructuredData({
  siteName,
  settings,
}: {
  siteName: string;
  settings: HomeData["settings"] | null;
}) {
  useEffect(() => {
    const ld = {
      "@context": "https://schema.org",
      "@graph": [
        {
          "@type": "LocalBusiness",
          "@id": "/#business",
          name: siteName,
          description: settings?.metaDescription || `${siteName} - bold creative work, booked online.`,
          email: settings?.contactEmail,
          telephone: settings?.phone || undefined,
          address: settings?.location ? { "@type": "PostalAddress", addressLocality: settings.location } : undefined,
          priceRange: "$$",
          opens: "Mo-Su 00:00-23:59",
          paymentAccepted: "Bank transfer, Mobile Money, Credit Card, PayPal",
        },
        {
          "@type": "WebSite",
          "@id": "/#website",
          name: siteName,
          url: "/",
          potentialAction: undefined,
        },
      ],
    };
    const el = document.createElement("script");
    el.type = "application/ld+json";
    el.id = "dy-jsonld";
    el.text = JSON.stringify(ld);
    document.head.appendChild(el);
    return () => {
      document.getElementById("dy-jsonld")?.remove();
    };
  }, [siteName, settings]);

  return null;
}
