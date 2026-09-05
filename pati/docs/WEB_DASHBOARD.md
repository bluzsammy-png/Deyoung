# WEB_DASHBOARD.md

The PATI dashboard is a **server-rendered, installable PWA** served by the
control plane itself. No build step, no npm, no framework, no CDNs - one
vanilla-JS page, by design (see docs/FREE_FIRST_POLICY.md).

## Pages & files

| Route | What it is |
|---|---|
| `/` | Live dashboard: submit jobs, stage progress, gallery, system stats |
| `/faq` | Plain-English FAQ (10 answers, FAQPage JSON-LD) |
| `/privacy` | Data honesty page (what stays local, what goes to Kaggle) |
| `/thank-you?job=ID` | Shown after a successful job submission |
| `/offline` | Service-worker fallback when the PC is unreachable |
| `/404` (any unknown path) | Custom HTML 404 (JSON is kept for `/api/*`) |
| `/robots.txt` | Disallow all (private system, by intent) |
| `/sitemap.xml` | Lists the three public pages |
| `/llms.txt` | Machine-readable description of PATI for AI assistants |
| `/manifest.webmanifest` | PWA manifest (standalone, icons, shortcuts) |
| `/sw.js` | Service worker: offline shell, asset caching, API never cached |
| `/assets/*` | Icons (192/512/maskable/apple/favicon), OG image, avatar |
| `/owner-photo.png` | Serves `DATA_DIR/owner-photo.png` if present, else a neutral placeholder |

## Security model

- Pages are public shells: they contain aggregate counts only.
- Every personal datum (jobs, artifacts, quotas) needs `Authorization: Bearer`.
- The dashboard stores your token in `localStorage` of the browser you paste
  it into, and nowhere else. "Forget" removes it.
- API responses are never cached by the service worker.

## Install as an app ($0, no store)

- **Android (Chrome/Edge):** open the dashboard -> tap *Install as app*
  (or menu -> *Add to Home screen*).
- **iOS (Safari):** open the dashboard -> Share -> *Add to Home Screen*.
- Launches full-screen with the PATI icon; works offline for the shell
  (data still needs the PC awake).

Why not native app stores? Apple charges $99/year and Google $25 - both
violate the $0 constitution. A PWA is installable on both platforms for free
and updates itself with the server.

## Custom domain ($0 if you own a domain)

1. Put your domain's DNS on Cloudflare (free plan).
2. `cloudflared tunnel create pati` and add ingress mapping your hostname
   to `http://localhost:8000` (see `installer/enable-tunnel.ps1`).
3. Browse to `https://pati.yourdomain.com` - done. No ports, no certificate
   work (Cloudflare terminates TLS).
- Owning no domain? The free `*.trycloudflare.com` URL works exactly the
  same; a *new* domain name is the only thing in this project that can cost
  money, and only if you choose to buy one.

## Owner checklist coverage (2026-09 request)

| Requested | Status |
|---|---|
| Web + mobile dashboard | Done - one responsive codebase |
| App for iOS + Android | Done as PWA (stores cost money; PWA is free) |
| Custom domain | Documented above ($0 with an existing domain) |
| Custom 404 page | Done (`/no-such-page` test) |
| Page source fixes / unique titles / meta descriptions / canonical | Done on every page, enforced by tests |
| Internal links | Header, footer, in-copy links between all pages |
| Thank-you page | Done, wired to real job submission |
| Clear CTA above the fold | Done - "What should PATI do?" + Run it |
| Case studies section | Adapted honestly: "Proven, not promised" flows (Flow 1 + Flow 2) |
| FAQ section | Done, 10 real questions + FAQPage schema |
| Real photos of me and the team | Adapted: owner photo slot (`owner-photo.png`); PATI is single-owner - no team exists to photograph |
| Social share images | OG/Twitter meta + generated 1200x630 share image |
| Response-time promise | Done - visible strip on every dashboard load |
| Proper icons | Generated icon set + favicon.svg |
| Alt text | On all content images |
| Breadcrumbs | On subpages (+ BreadcrumbList-ready markup) |
| robots.txt / sitemap.xml / llms.txt | Done (robots disallows all on purpose) |
| Local business schema | Adapted to `SoftwareApplication` JSON-LD with `price: 0` - PATI is not a local business |
| Google Analytics | Replaced by a local-only visit counter in PATI's DB - third-party analytics on a private dashboard would defeat its privacy promise |
| Maps and directions | Not applicable - PATI is software on your PC, not a place |
| Sticky mobile CTA | Done - "+ New job" bar on phones |
| Remove Vite/React titles | N/A and satisfied: no framework, no boilerplate titles |
| Console errors / source maps / bundle size | 0 console errors (Playwright-verified), no source maps produced, the whole UI is a few KB of inline HTML/CSS/JS |
| Whole-site error check | Automated: 69 pytest tests + Playwright crawl of every route |

## Implementation notes

- Source: `pati_api/webapp.py` (pages), `pati_api/app.py` (routes),
  `pati_api/static/` (binary assets, generated once by
  `scripts/gen_dashboard_assets.py` - users need no Pillow).
- Tests: `tests/test_dashboard.py` (15 checks incl. unique titles, PWA files,
  404 semantics, sitemap, llms.txt, visit counter).
- The visit counter is a single `kv` row; it exists to prove analytics can
  be honest and local.
