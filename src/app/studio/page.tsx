import type { Metadata } from "next";
import { StudioView } from "@/components/site/studio";

export const metadata: Metadata = {
  title: "Your Studio - DeYoung",
  robots: { index: false, follow: false },
};

/**
 * The customer studio at its own URL: /studio
 * (the hash route /#/studio keeps working for backwards compatibility).
 */
export default function StudioPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <StudioView />
    </div>
  );
}
