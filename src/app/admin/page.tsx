import type { Metadata } from "next";
import { AdminApp } from "@/components/site/admin/admin-app";

export const metadata: Metadata = {
  title: "Admin Panel - DeYoung",
  robots: { index: false, follow: false },
};

/**
 * The separate admin panel at its own URL: /admin
 * (the hash route /#/admin keeps working for backwards compatibility).
 * Self-contained: login form + owner dashboard, no public site chrome.
 */
export default function AdminPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <AdminApp />
    </div>
  );
}
