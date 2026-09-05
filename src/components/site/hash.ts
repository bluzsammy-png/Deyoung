"use client";

import { useEffect, useState } from "react";

export type Route =
  | { name: "home"; anchor?: string }
  | { name: "plans" }
  | { name: "book"; serviceId?: string }
  | { name: "subscribe"; planCode?: string }
  | { name: "request" }
  | { name: "studio" }
  | { name: "legal"; doc: string }
  | { name: "thanks"; bookingId?: string; paid?: boolean }
  | { name: "admin" };

/** Tiny hash router - the whole app lives on `/` (preview-friendly). */
export function parseHash(hash: string): Route {
  const h = hash.replace(/^#\/?/, "");
  const [path, query] = h.split("?");
  const params = new URLSearchParams(query || "");
  switch (path) {
    case "plans":
      // "See plans" - a real plans page of its own: tapping it from anywhere
      // (home, studio, request, book) lands straight on the plans, never on
      // top of the homepage.
      return { name: "plans" };
    case "gallery":
      return { name: "home", anchor: "gallery" };
    case "book":
      return { name: "book", serviceId: params.get("service") || undefined };
    case "subscribe":
      return { name: "subscribe", planCode: params.get("plan") || undefined };
    case "request":
      return { name: "request" };
    case "studio":
      return { name: "studio" };
    case "privacy":
    case "terms":
    case "refunds":
    case "voice-license":
      return { name: "legal", doc: path };
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
    default:
      return { name: "home" };
  }
}

/** Smooth-scroll to an in-page anchor, retrying while it renders in. */
export function scrollToAnchor(id: string) {
  let tries = 0;
  const tick = () => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    } else if (tries++ < 40) {
      requestAnimationFrame(tick);
    }
  };
  requestAnimationFrame(tick);
}

export function useHashRoute(): Route {
  const [route, setRoute] = useState<Route>(() =>
    typeof window === "undefined" ? { name: "home" } : parseHash(window.location.hash)
  );

  useEffect(() => {
    const onChange = () => {
      const next = parseHash(window.location.hash);
      setRoute(next);
      if (next.name !== "home") {
        window.scrollTo({ top: 0 });
      } else if (next.anchor) {
        // e.g. #plans / #gallery - keep the home view, glide to the section.
        scrollToAnchor(next.anchor);
      } else {
        window.scrollTo({ top: 0 });
      }
    };
    // handle a page loaded directly with an anchor hash (e.g. /#plans)
    const initial = parseHash(window.location.hash);
    if (initial.name === "home" && initial.anchor) scrollToAnchor(initial.anchor);
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  return route;
}

export function go(hash: string) {
  // Standalone routes (/studio, /admin) have no hash app - jump back to the
  // single-page app on / and let its router handle the hash.
  if (typeof window !== "undefined" && window.location.pathname !== "/") {
    window.location.href = "/" + (hash.startsWith("#") ? hash : "#" + hash);
    return;
  }
  window.location.hash = hash;
}
