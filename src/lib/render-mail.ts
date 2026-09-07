/**
 * Render notification emails — fired from the worker job pipeline.
 *
 * - render-done: the moment a worker delivers the finished master, the owner
 *   of the request gets their film link (dashboard — the file itself stays
 *   private-by-default behind account auth).
 * - render-failed: honest failure notice with what happened.
 *
 * Non-fatal by design (same transport as all AgentMail sends): if the key is
 * missing or the API is down, the render still succeeds and the film still
 * appears in the dashboard. In dev (no AGENTMAIL_API_KEY) these are no-ops.
 */

import { sendOwnerEmail } from "@/lib/agentmail";

const SITE = process.env.NEXT_PUBLIC_SITE_URL || "https://deyoungltd.site";

type RenderMailRequest = {
  id: string;
  email: string;
  prompt: string;
  seconds: number;
  resolution: string;
  withAudio: boolean;
};

const DASH_URL = `${SITE}/#dashboard`;

export async function sendRenderDoneEmail(r: RenderMailRequest): Promise<boolean> {
  const title = r.prompt.length > 70 ? r.prompt.slice(0, 69) + "…" : r.prompt;
  const sent = await sendOwnerEmail({
    to: r.email,
    subject: "Your DeYoung film is ready",
    text: [
      "Your film just came off the render farm.",
      "",
      `Shot: ${title}`,
      `${r.seconds}s · ${r.resolution}${r.withAudio ? " · with audio" : ""}`,
      "",
      `Watch it here: ${DASH_URL}`,
      "(Sign in with the email you subscribed with, then open Dashboard.)",
      "",
      "— DeYoung AI Film Studio",
    ].join("\n"),
    html: [
      '<div style="font-family:Arial,Helvetica,sans-serif;background:#0a0a0a;padding:28px;color:#fafafa">',
      '  <div style="max-width:520px;margin:0 auto">',
      '    <p style="font-size:11px;letter-spacing:.25em;color:#ef4444;font-weight:900;margin:0 0 8px">DEYOUNG · AI FILM STUDIO</p>',
      '    <h1 style="font-size:22px;margin:0 0 12px;color:#fafafa">Your film is ready</h1>',
      `    <p style="font-size:14px;line-height:1.6;color:#d4d4d4;margin:0 0 12px">${title}</p>`,
      `    <p style="font-size:13px;color:#a3a3a3;margin:0 0 20px">${r.seconds}s · ${r.resolution}${r.withAudio ? " · with audio" : ""}</p>`,
      `    <a href="${DASH_URL}" style="display:inline-block;background:#dc2626;color:#ffffff;font-weight:bold;font-size:14px;padding:12px 22px;border-radius:12px;text-decoration:none">Watch your film</a>`,
      '    <p style="font-size:12px;color:#737373;margin-top:20px">Sign in with your subscribed email, then open your Dashboard. Renders stay private to your account.</p>',
      "  </div>",
      "</div>",
    ].join(""),
  });
  if (sent) console.info(`[render-mail] done email sent to ${r.email} (request ${r.id})`);
  else console.info(`[render-mail] done email skipped/unavailable for ${r.email} (request ${r.id})`);
  return sent;
}

export async function sendRenderFailedEmail(r: RenderMailRequest, reason: string): Promise<boolean> {
  const sent = await sendOwnerEmail({
    to: r.email,
    subject: "Your DeYoung render hit a snag — we're on it",
    text: [
      "Your render could not be completed this run.",
      "",
      `Prompt: ${r.prompt.slice(0, 200)}`,
      `Reason: ${reason.slice(0, 300)}`,
      "",
      "A failed render does not use your monthly plan videos — only renders in the",
      "queue or delivered count. The owner can requeue it; you'll get the ready",
      "email the moment it comes off the farm.",
      "",
      "— DeYoung AI Film Studio",
    ].join("\n"),
  });
  if (sent) console.info(`[render-mail] failure email sent to ${r.email} (request ${r.id})`);
  else console.info(`[render-mail] failure email skipped/unavailable for ${r.email} (request ${r.id})`);
  return sent;
}
