import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import { Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";

// Brand display + body font: Archivo variable (wght 100-900), self-hosted.
// Keeps the --font-geist-sans variable name so existing styles apply unchanged.
const archivo = localFont({
  src: "./fonts/Archivo.ttf",
  weight: "100 900",
  variable: "--font-geist-sans",
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000"),
  title: {
    default: "DeYoung - AI Video Up to 60 Seconds in One Pass",
    template: "%s | DeYoung",
  },
  description:
    "DeYoung - AI video generation up to 60 seconds in one pass, where other models stop at 15. Subscribe monthly (Beginner, Pro, Elite) or book creative services. Pay locally or internationally.",
  keywords: [
    "DeYoung",
    "AI video generation",
    "60 second AI video",
    "text to video",
    "video subscription",
    "photography",
    "brand design",
    "book online",
  ],
  authors: [{ name: "DeYoung" }],
  creator: "DeYoung",
  applicationName: "DeYoung",
  manifest: "/manifest.webmanifest",
  alternates: { canonical: "/" },
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/favicon-64.png", sizes: "64x64", type: "image/png" },
    ],
    apple: "/apple-touch-icon.png",
  },
  openGraph: {
    title: "DeYoung - AI Video Up to 60 Seconds in One Pass",
    description:
      "Where other models stop at 15 seconds, DeYoung renders up to 60 in a single pass. Subscribe monthly, pay locally or internationally.",
    url: "/",
    siteName: "DeYoung",
    images: [{ url: "/img/og-image.png", width: 1200, height: 630, alt: "DeYoung - AI video generation and creative services" }],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "DeYoung - AI Video Up to 60 Seconds in One Pass",
    description: "Subscribe monthly: Beginner, Pro, Elite. Pay locally or internationally.",
    images: ["/img/og-image.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, "max-image-preview": "large" },
  },
};

export const viewport: Viewport = {
  themeColor: "#0A0A0A",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${archivo.variable} ${geistMono.variable} antialiased bg-background text-foreground min-h-screen flex flex-col`}
      >
        {children}
        <Toaster position="top-center" richColors closeButton />
      </body>
    </html>
  );
}
