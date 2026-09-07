"use client";

import { useEffect, useState } from "react";

export type Route =
  | { name: "home" }
  | { name: "book"; serviceId?: string }
  | { name: "subscribe"; planCode?: string }
  | { name: "request" }
  | { name: "privacy" }
  | { name: "thanks"; bookingId?: string; paid?: boolean }
  | { name: "admin" }
  | { name: "signin"; error?: string }
  | { name: "signup"; planCode?: string }
  | { name: "dashboard" }
  | { name: "studio"; projectId?: string };

/** Tiny hash router — the whole app lives on `/` (preview-friendly). */
export function parseHash(hash: string): Route {
  const h = hash.replace(/^#\/?/, "");
  const [path, query] = h.split("?");
  const params = new URLSearchParams(query || "");
  switch (path) {
    case "book":
      return { name: "book", serviceId: params.get("service") || undefined };
    case "subscribe":
      return { name: "subscribe", planCode: params.get("plan") || undefined };
    case "request":
      return { name: "request" };
    case "privacy":
      return { name: "privacy" };
    case "thanks": {
      const raw = params.get("paid");
      return {
        name: "thanks",
        bookingId: params.get("b") || undefined,
        paid: raw === "1" || raw === "true",
      };
    }
    case "admin":
      return { name: "admin" };
    case "signin":
      return { name: "signin", error: params.get("error") || undefined };
    case "signup":
      return { name: "signup", planCode: params.get("plan") || undefined };
    case "dashboard":
      return { name: "dashboard" };
    case "studio":
      return { name: "studio", projectId: params.get("p") || undefined };
    default:
      return { name: "home" };
  }
}

export function useHashRoute(): Route {
  const [route, setRoute] = useState<Route>(() =>
    typeof window === "undefined" ? { name: "home" } : parseHash(window.location.hash)
  );

  useEffect(() => {
    const onChange = () => {
      const next = parseHash(window.location.hash);
      setRoute(next);
      if (next.name !== "home") window.scrollTo({ top: 0 });
    };
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  return route;
}

export function go(hash: string) {
  window.location.hash = hash;
}
