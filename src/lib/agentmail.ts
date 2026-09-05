/**
 * AgentMail integration - sends site notifications (contact messages, new bookings)
 * to the owner's AgentMail inbox. Non-fatal by design: if the key is missing or the
 * API is unreachable, the site keeps working and the message still lands in the DB.
 *
 * Env:
 *   AGENTMAIL_API_KEY - organization API key (am_us_…)
 *   AGENTMAIL_INBOX   - owner inbox id (default: deyoungsltd@agentmail.to)
 */

const API_BASE = process.env.AGENTMAIL_API_URL || "https://api.agentmail.to";
const DEFAULT_INBOX = "deyoungsltd@agentmail.to";

export type OwnerMail = {
  subject: string;
  text: string;
  html?: string;
  /** Customer address so the owner can reply straight from the inbox. */
  replyTo?: string;
  /** Override recipient (defaults to the owner inbox). */
  to?: string;
};

export function agentMailConfigured(): boolean {
  return Boolean(process.env.AGENTMAIL_API_KEY);
}

/**
 * Fire-and-forget owner notification. Never throws.
 * Returns true when the API accepted the message.
 */
export async function sendOwnerEmail(mail: OwnerMail): Promise<boolean> {
  const key = process.env.AGENTMAIL_API_KEY;
  // Skip during static prerender/build phase - mail is runtime-only.
  if (!key || process.env.NEXT_PHASE === "phase-production-build") return false;

  const inbox = process.env.AGENTMAIL_INBOX || DEFAULT_INBOX;
  const to = mail.to || inbox;

  try {
    const res = await fetch(`${API_BASE}/v0/inboxes/${encodeURIComponent(inbox)}/messages/send`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${key}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        to: [to],
        reply_to: mail.replyTo ? [mail.replyTo] : undefined,
        subject: mail.subject,
        text: mail.text,
        html: mail.html,
      }),
      cache: "no-store",
      // Don't let a slow mail call hold the HTTP response for long.
      signal: AbortSignal.timeout(8000),
    });
    if (!res.ok) {
      console.error("[agentmail] send failed", res.status, (await res.text()).slice(0, 200));
      return false;
    }
    return true;
  } catch (err) {
    console.error("[agentmail] send error", err instanceof Error ? err.message : err);
    return false;
  }
}
