"use client";

import { useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { LogoMark } from "./logo";

/**
 * Official legal documents - Privacy Policy (aligned with the Nigeria Data
 * Protection Act, 2023), Terms of Service, Refund Policy.
 *
 * FACTUALITY RULE: every statement below describes what this system actually
 * does today (Railway hosting, Supabase Postgres in the EU, Paystack payments,
 * scrypt password hashing, render queue logs). Nothing aspirational is claimed.
 */

type Doc = { id: string; label: string; body: React.ReactNode };

function H({ children }: { children: React.ReactNode }) {
  return <h2 className="mt-10 text-xl font-black uppercase tracking-tight text-[var(--brand-black)]">{children}</h2>;
}
function P({ children }: { children: React.ReactNode }) {
  return <p className="mt-4 text-sm md:text-base leading-relaxed text-neutral-700">{children}</p>;
}
function L({ items }: { items: React.ReactNode[] }) {
  return (
    <ul className="mt-4 space-y-2">
      {items.map((it, i) => (
        <li key={i} className="flex gap-2 text-sm md:text-base leading-relaxed text-neutral-700">
          <span className="mt-2 h-1.5 w-1.5 shrink-0 bg-primary" aria-hidden />
          <span>{it}</span>
        </li>
      ))}
    </ul>
  );
}

const UPDATED = "5 September 2026";

const DOCS: Doc[] = [
  {
    id: "privacy",
    label: "Privacy Policy",
    body: (
      <>
        <p className="text-xs font-bold uppercase tracking-widest text-neutral-400">Last updated: {UPDATED}</p>
        <P>
          This Privacy Policy explains how DeYoung (&ldquo;we&rdquo;, &ldquo;us&rdquo;) collects, uses, shares and protects
          personal data when you use this website and the DeYoung studio. It is written to align with the Nigeria Data
          Protection Act, 2023 (NDPA) and its data-subject rights. If anything here is unclear, contact us before using
          the service - see &ldquo;Contact&rdquo; at the end.
        </P>

        <H>1. Who we are</H>
        <P>
          DeYoung is an AI video generation service and creative studio operated by an independent business owner. For
          the purposes of the NDPA, DeYoung is the data controller of the personal data described in this policy. Our
          hosting and infrastructure providers (see &ldquo;Where your data lives&rdquo;) act as our processors.
        </P>

        <H>2. What we collect</H>
        <L items={[
          <>Account data: your name, email address and (optionally) phone number and avatar image. Your password is stored only as a scrypt hash - it cannot be read by us. If you sign in with Google, we store your Google account identifier and email; we never see your Google password.</>,
          <>Script and render data: the scripts/prompts you submit, your chosen engine (deyo.1-deyo-Max), length, voice and character reference images, plus render logs (queue position, progress, delivery events, quality-check results).</>,
          <>Voice-clone licence data (only if you license a voice): the voice sample you upload, your recorded consent statement, and - for a voice belonging to someone else - their written permission document. A voiceprint is biometric-class personal data, so we collect it only with your explicit consent and use it only for your own renders. See the Voice Clone Licence &amp; Consent Policy.</>,
          <>Payment data: payments are processed by Paystack. We receive and store your payment reference, the amount, the plan purchased and the payment status. We never see or store your card number, BVN or bank credentials.</>,
          <>Support conversations: messages you exchange with live support inside the studio.</>,
          <>Operational logs: standard server logs kept by our hosting provider for security and reliability.</>,
        ]} />

        <H>3. Why we process it (lawful basis)</H>
        <L items={[
          <>To provide the service you subscribed to - creating your account, queueing and rendering your videos, delivering downloads (performance of a contract).</>,
          <>To take payments and prevent fraud (performance of a contract and our legitimate interests).</>,
          <>To answer support requests (performance of a contract).</>,
          <>To keep the platform secure and debug failures (legitimate interests).</>,
          <>To send service notices about your account or renders. We do not sell your data and we do not run third-party advertising trackers on this site.</>,
        ]} />

        <H>4. Where your data lives</H>
        <P>
          The application runs on Railway (EU region) with a Supabase Postgres database (EU region). Uploaded images and
          finished videos are stored on the application server and served through it. Payments are processed by Paystack
          (Nigeria). This means your data may be processed outside Nigeria by these providers on our instructions; we
          select reputable providers and keep transfers limited to what the service needs.
        </P>

        <H>5. AI processing of your scripts</H>
        <P>
          Your scripts and reference images are processed by our render pipeline to produce your video. Renders run on
          worker machines operated for DeYoung (our own GPU workers or contracted compute such as Kaggle-provided
          notebooks running open-source models). We do not knowingly send your data to third-party generators without
          telling you in the product. Finished videos are private to your account until you choose to download or share
          them.
        </P>

        <H>6. How long we keep data</H>
        <L items={[
          <>Account data: kept while your account is open. You can request deletion at any time.</>,
          <>Render history and delivered videos: kept so you can re-download them; deleted on request or when your account is deleted.</>,
          <>Voice-clone licence evidence: kept while the voice licence is active. When you revoke a voice (or your account is deleted), the sample, consent recording and written permission are deleted with it.</>,
          <>Payment references: kept as long as needed for accounting and dispute resolution.</>,
          <>Support messages: kept while your account is open, then deleted with the account.</>,
        ]} />

        <H>7. Your rights under the NDPA</H>
        <P>You may contact us at any time to:</P>
        <L items={[
          <>access the personal data we hold about you and receive a copy;</>,
          <>correct inaccurate data (you can also edit your name, phone and avatar yourself in Profile);</>,
          <>delete your account and personal data (subject to retention we must keep for accounting);</>,
          <>object to or restrict certain processing;</>,
          <>lodge a complaint with the Nigeria Data Protection Commission (NDPC).</>,
        ]} />
        <P>
          We respond to verified requests within a reasonable timeframe and at no cost to you. Children&apos;s privacy:
          the service is not directed at children under 13 (and under 18 requires a parent/guardian&apos;s consent for
          account creation), in line with the NDPA&apos;s children&apos;s protections.
        </P>

        <H>8. Security</H>
        <L items={[
          <>Passwords are hashed with scrypt and never stored in plain text.</>,
          <>Sessions use signed, HTTP-only cookies. Admin and customer sessions are separate.</>,
          <>Payments run on Paystack&apos;s PCI-DSS compliant infrastructure; card data never touches our servers.</>,
          <>Uploads are restricted to image formats, size-capped, and served through validated routes.</>,
        ]} />

        <H>9. Contact</H>
        <P>
          Data protection contact: the site&apos;s contact email shown in the &ldquo;Let&apos;s Talk&rdquo; section of
          this website. If you are in Nigeria you may also escalate to the NDPC.
        </P>
      </>
    ),
  },
  {
    id: "terms",
    label: "Terms of Service",
    body: (
      <>
        <p className="text-xs font-bold uppercase tracking-widest text-neutral-400">Last updated: {UPDATED}</p>
        <P>
          These Terms govern your use of the DeYoung website, studio and video generation service. By creating an
          account, subscribing or booking, you accept these Terms.
        </P>

        <H>1. The service</H>
        <P>
          DeYoung turns your written scripts into short videos using automated rendering pipelines, up to 60 seconds in
          a single pass depending on your chosen engine and plan. Output quality, style and delivery time depend on the
          engine selected and the current render queue. Queue position and honest engine telemetry are shown in your
          studio.
        </P>

        <H>2. Accounts</H>
        <P>
          You must give accurate information, keep your password confidential and be at least 18 (or have a
          parent/guardian&apos;s consent). You are responsible for activity under your account. Tell us immediately if
          you suspect unauthorised access.
        </P>

        <H>3. Subscriptions, quotas and fair use</H>
        <P>
          Plans include a monthly video quota, per-video length cap, resolution and queue priority, shown at checkout
          and in your studio. Quotas reset each subscription period and do not roll over. The price you lock stays
          locked while your subscription remains active. We may suspend accounts that abuse the service (for example
          automated scraping, reselling renders as a competing service, or attempting to bypass queue limits).
        </P>

        <H>4. Acceptable use</H>
        <P>You must not submit scripts or images that:</P>
        <L items={[
          <>are unlawful, hateful, harassing, sexually explicit or that sexualise minors;</>,
          <>infringe someone else&apos;s copyright, trademark or privacy;</>,
          <>impersonate real people without their consent (voice cloning of a real person&apos;s voice is only allowed under the{" "}
          <a href="#voice-license" className="underline underline-offset-2 font-bold text-primary">Voice Clone Licence</a>, with the owner&apos;s recorded consent);</>,
          <>spread misinformation intended to cause harm.</>,
        ]} />
        <P>We may cancel renders that breach this section without refund for the affected render.</P>

        <H>5. Your content and your outputs</H>
        <P>
          You keep the rights to the scripts and images you upload. You receive the finished videos for your use,
          including commercial use on plans that include a commercial licence. DeYoung may display work samples publicly
          only with your permission, or from the portfolio samples we produced ourselves.
        </P>

        <H>6. Availability</H>
        <P>
          Rendering depends on worker capacity (including free GPU lanes). We show live queue state instead of
          promising exact delivery times, and we keep the queue honest and first-ordered by plan priority. If a render
          fails on our side, it is retried or your quota is restored - see the Refund Policy.
        </P>

        <H>7. Liability</H>
        <P>
          To the maximum extent permitted by law, DeYoung is not liable for indirect or consequential losses. Our total
          liability for any claim is limited to the amount you paid us in the three months before the claim. Nothing
          limits liability that cannot be limited by law.
        </P>

        <H>8. Changes and termination</H>
        <P>
          We may update these Terms with notice on this page; continued use means acceptance. You may cancel your
          subscription at any time - access continues to the end of the paid period.
        </P>
      </>
    ),
  },
  {
    id: "voice-license",
    label: "Voice Clone Licence",
    body: (
      <>
        <p className="text-xs font-bold uppercase tracking-widest text-neutral-400">Last updated: {UPDATED}</p>
        <P>
          This Voice Clone Licence &amp; Consent Policy (“Licence”) governs voice cloning on DeYoung. It
          forms part of our Terms of Service and our Privacy Policy. Voice cloning is a privilege built on
          consent and evidence: we only allow it when the person whose voice it is has clearly said yes, and
          we keep the proof. This is the same discipline the major voice platforms apply, and it reflects how
          the law treats a person’s voice: as something that belongs to them.
        </P>

        <H>1. What you may license</H>
        <L items={[
          <>Your own voice - instantly. You upload a voice sample and a consent recording in which you read the scripted statement displayed at upload. When both are on file and you accept this Licence, the voice is licensed to your account.</>,
          <>Someone else’s voice - only with written permission. You must upload the voice owner’s signed permission document together with their consent recording. The licence stays inactive until the DeYoung owner reviews the document and approves it. Uploading a third-party voice without genuine written permission is a serious breach (see §5).</>,
          <>Nothing else. Fictional or synthetic voice presets are provided by the engine itself; they are not voice clones and are not covered by this Licence.</>,
        ]} />

        <H>2. The consent statement</H>
        <P>
          The consent recording is the licence evidence. You must read the exact statement shown at upload -
          it names you, confirms you own the voice, authorises DeYoung to create a clone for your own account
          use, and notes that you can revoke the licence at any time. We keep this recording for as long as the
          licence is active. Do not read a script prepared for someone else, and do not submit a recording of
          another person - that is exactly what this evidence exists to prevent.
        </P>

        <H>3. Scope of the licence you grant</H>
        <L items={[
          <>You grant DeYoung a licence to store your voiceprint and use it solely to render videos you request on your own account.</>,
          <>The licence is personal to your account. It is not transferable, and voiceprints cannot be shared, sold or moved to other accounts or services.</>,
          <>You keep ownership of your voice. Nothing in this Licence gives DeYoung the right to use your voice for anything you did not request, including marketing, without a separate written agreement.</>,
          <>You may revoke at any time from your Profile (“Voice licenses” then “Revoke”). Revocation stops future renders with that voice; renders already requested while the licence was active may still complete.</>,
        ]} />

        <H>4. Prohibited use</H>
        <P>You must never use a cloned voice to:</P>
        <L items={[
          <>impersonate a real person - including celebrities, public figures, officials or anyone who did not license that voice;</>,
          <>deceive: scams, fake emergency or bank calls, fraudulent “proof”, fabricated statements attributed to real people;</>,
          <>political or election manipulation, or content designed to mislead about matters of public interest;</>,
          <>harass, defame, threaten or sexually exploit;</>,
          <>circumvent plan limits, resell rendering, or otherwise abuse the platform;</>,
        ]} />
        <P>
          Breaching this section means immediate licence revocation and, where the law or these Terms allow,
          account suspension. Serious cases may be reported to the relevant authorities.
        </P>

        <H>5. Audit and enforcement</H>
        <P>
          Every licence is auditable: DeYoung’s owner can listen to the consent evidence, flag a licence for
          review, reject it, revoke it, or reinstate it. We treat unauthorised cloning of another person’s
          voice with maximum severity. A person’s voice is legally protected property in many places - for
          example, right-of-publicity laws such as Tennessee’s ELVIS Act (2024) specifically protect voices
          from unauthorised AI cloning, and platforms can be held liable for enabling it - so evidence and
          audit trails are not optional extras; they are the licence itself.
        </P>

        <H>6. Your data rights over the voiceprint</H>
        <P>
          Under the Nigeria Data Protection Act, 2023 a voiceprint is treated with sensitive-data discipline.
          You have the same rights over it as over the rest of your data: access a copy of what we hold, ask
          for corrections, revoke the licence, and have the sample, consent recording and written permission
          deleted when the licence ends. See the Privacy Policy for how to exercise these rights.
        </P>

        <H>7. Changes</H>
        <P>
          If we change this Licence, existing licences continue under the version they were filed with unless
          you accept the new version at your next upload. Questions? Message live support in your studio.
        </P>
      </>
    ),
  },
  {
    id: "refunds",
    label: "Refund Policy",
    body: (
      <>
        <p className="text-xs font-bold uppercase tracking-widest text-neutral-400">Last updated: {UPDATED}</p>
        <P>
          We want you to feel safe paying DeYoung. This policy explains exactly when money comes back to you. It forms
          part of our Terms of Service.
        </P>

        <H>Subscriptions</H>
        <L items={[
          <>If a technical fault on our side makes the service unusable for your whole first period, we refund that period in full.</>,
          <>If a render fails on our side and cannot be retried or delivered, the video is restored to your quota or refunded pro-rata - your choice.</>,
          <>If you cancel mid-period, your subscription runs to the end of the period you paid for and does not renew. Unused quota for the paid period is not cash-refundable, because render capacity is reserved for you in the queue.</>,
        ]} />

        <H>Booked services (portrait sessions, brand packs, event coverage)</H>
        <L items={[
          <>Full refund if you cancel more than 72 hours before the scheduled date.</>,
          <>50% refund for cancellations within 72 hours.</>,
          <>Full refund if we cancel or cannot deliver.</>,
        ]} />

        <H>How refunds are paid</H>
        <P>
          Refunds go back through the original payment channel (Paystack, bank transfer or mobile money). Allow 5-10
          working days for the money to appear, depending on your bank. To request a refund, message live support in
          your studio or use the site contact - include your payment reference.
        </P>
      </>
    ),
  },
];

export function LegalView({ initial }: { initial: string }) {
  const [active, setActive] = useState(DOCS.some((d) => d.id === initial) ? initial : "privacy");
  useEffect(() => {
    if (DOCS.some((d) => d.id === initial)) setActive(initial);
  }, [initial]);
  const doc = DOCS.find((d) => d.id === active)!;

  return (
    <main className="flex-1 bg-white">
      <div className="bg-[var(--brand-black)] text-white py-12">
        <div className="mx-auto max-w-3xl px-4">
          <p className="inline-flex items-center gap-2 text-xs font-black uppercase tracking-[0.3em] text-primary">
            <ShieldCheck className="h-4 w-4" aria-hidden /> Official documents
          </p>
          <h1 className="mt-3 text-3xl md:text-4xl font-black uppercase tracking-tight">The fine print, in plain language</h1>
        </div>
      </div>
      <div className="mx-auto max-w-3xl px-4 py-10">
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Legal documents">
          {DOCS.map((d) => (
            <button
              key={d.id}
              role="tab"
              aria-selected={active === d.id}
              onClick={() => setActive(d.id)}
              className={`px-4 py-2 text-xs font-black uppercase tracking-widest border-2 transition-colors ${
                active === d.id ? "bg-[var(--brand-black)] border-[var(--brand-black)] text-white" : "border-neutral-200 text-neutral-600 hover:border-primary hover:text-primary"
              }`}
            >
              {d.label}
            </button>
          ))}
        </div>
        <article className="mt-8">{doc.body}</article>
        <p className="mt-12 flex items-center gap-2 text-xs text-neutral-400">
          <LogoMark className="h-4 w-4" aria-hidden /> DeYoung - {doc.label} · {UPDATED}
        </p>
      </div>
    </main>
  );
}
