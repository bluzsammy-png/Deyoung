# DeYoung — AI Video Studio

Public booking + subscription site for DeYoung: **60-second single-pass AI video generation** (where other engines stop at 15s) plus bold creative services.

## Highlights

- **60s AI film engine** — Amara & Kojo, real speaking characters, featured in the hero film (`public/video/deyoung-film-web.mp4`)
- **Tiered subscriptions** — Beginner / Pro / Elite with every limit owner-editable and enforced server-side
- **Queue-first rendering** — honest ETA, daily GPU-minute budget, dedup cache (repeat renders cost zero GPU)
- **Payments your way** — manual bank / mobile money (works today), plus one-click Paystack, Flutterwave, PayPal, Stripe
- **Owner-only admin** — `/admin` panel: bookings, messages, gallery, plans, subscribers, video queue, payments, site settings
- **Mobile + web experience** — installable PWA, sticky mobile CTA, responsive from 360px up

## Stack

Next.js (App Router) · TypeScript · Tailwind · shadcn/ui · Prisma (SQLite) · scrypt auth with HMAC session cookies

## Run

```bash
bun install   # or npm install
npx prisma db push && npx prisma db seed
npm run dev   # http://localhost:3000
```

Owner login (change immediately): `admin@deyoung.site` / `deyoung123`

## Creative pipeline (campaign assets)

`scripts/` contains the full regeneration toolchain:

- `film_stills.mjs` → character/scene stills (image gen)
- `film_submit.mjs` / `film_poll.mjs` → 8-scene video generation with rolling rate-limit handling
- `assemble_film.py` → grade, subtitles, end card, score, master + web encodes
- `social_posts.py` → the 7 launch cards in `download/social/` (mobile + web device mockups)
