# PATI Project Worklog

---
Task ID: 13
Agent: main (Super Z)
Task: 补齐 PATI 剩余全部文档（docs/ + 仓库根 AGENTS 系列）

Work Log:
- 批次1：写 docs/INSTALL.md（先决条件、install.ps1、12步向导逐步表、手动安装、验证、Cloudflare Tunnel、Kaggle token、服务自启、卸载）、docs/TROUBLESHOOTING.md（8 大类症状→原因→修复表 + 诊断命令清单）、docs/FAILURE_RECOVERY.md（设计原则、14 项故障矩阵、作业恢复语义、4 个手动恢复流程、"恢复不做的事"）、docs/DEPLOYMENT.md（5 种 $0 拓扑 A–E、选型表、生产卫生、反目标）
- 批次2：写 docs/FREE_FIRST_POLICY.md（$0 宪法：硬常量/精确含义/六层强制机制/免费资源表/决策流程/反模式/超 free 出路）、docs/LICENSE_POLICY.md（MIT、依赖许可表、模型三桶许可规则、外部服务 ToS、产物归属、合规工作流）、docs/OPEN_SOURCE_POLICY.md（公开范围、贡献流程、决策记录、发布策略、反目标）、docs/COMMERCIALIZATION.md（当前 $0 状态、6 种兼容商业途径、6 条防火墙、诚实经济学、fork 义务）、docs/MULTI_TENANT_SAAS.md（已内建单运营者多身份原语、SaaS fork 真实成本、"默认不做"的三个理由、中间地带、fork 决策规则）
- 批次3：写 docs/ROADMAP.md（M0✅ 已交付 / M1 加固 / M2 免费算力扩容 / M3 生态 / M4 礼貌规模化 + 永久拒绝清单）、docs/IMPLEMENTATION_PLAN.md（0研究→1契约→2控制面→3执行面→4证明→5文档 的实际执行记录含死锁教训）、docs/DEV_ENVIRONMENT.md（工具链、10分钟上手、仓库地图、日常命令、三类常见 PR、调试技巧、done 定义）、docs/CI_CD.md（6 阶段管线、参考 Actions YAML、本地等价命令、发布 zip 清单、CI 不做的事）
- 批次4：写 docs/BENCHMARKING.md（8 维指标、方法学、2026-09-02 基线表、回归门槛、诚实警告）、docs/EVALUATION.md（golden task 格式、按能力种子集 68 任务、计分与三条健康红线、运行时机、记录规则）、docs/RESEARCH_ENGINE.md（研究先于实现的循环、证据源层级、6 项判定 rubric、台账格式、季度再校准、请求模板）、docs/COMPETITOR_RESEARCH.md（6 种竞品原型对比、PATI 5 个真正罕见点、诚实的劣势、定位声明、季度更新政策）
- 批次5：写 docs/AGENTS.md（AI 编码代理权威规则：5 条不可协商、2分钟仓库导览、变更流程、常用命令、常见错误清单、遇钱流程、提交纪律）；仓库根写 AGENTS.md（指针）+ CLAUDE.md / GEMINI.md / CODEX.md / CURSOR.md / COPILOT.md（各工具快速适配，均指向 docs/AGENTS.md）
- 更新 README 文档地图（入门/架构/政策/流程/AI 代理五区完整索引）
- 补写仓库根 LICENSE（MIT + 第三方归属声明）
- 回归验证：python -m pytest tests -q → 46 passed in 13.88s；python examples/e2e_demo.py → FLOW 1 PROVEN END-TO-END

Stage Summary:
- docs/ 从 27 份增至 43 份，README 索引同步；仓库根新增 AGENTS.md + 5 个工具入口 + LICENSE
- 全部文档与代码事实一致（端口 8000、46 测试、240 GPU-min/天、RESOURCE_UNAVAILABLE 语义等）
- 46 测试全绿，流程1 冒烟演示通过

---
Task ID: 14
Agent: main (Super Z)
Task: 打包交付 zip 到 download/，记录 worklog，最终总结

Work Log:
- 清理打包排除项（.venv / __pycache__ / .pytest_cache / data / .git / pati_workspace）
- 生成 /home/z/my-project/download/PATI-zero-cost-infrastructure.zip：162 文件，226KB
- 校验 zip：43 份 docs 齐全、AGENTS 系列与 LICENSE 在根目录、无 venv/pycache 垃圾
- 写入本 worklog

Stage Summary:
- 交付物：/home/z/my-project/download/PATI-zero-cost-infrastructure.zip（完整 PATI 系统：控制面、SDK/CLI/适配器、本地代理、Kaggle/容器 worker、连接器、MCP、15 JSON Schema、installer、4 个可运行演示、46 测试、43 份文档）
- 项目全部 14 项 todo 完成

---
Task ID: 15
Agent: main (Super Z)
Task: Kaggle credential compatibility fix (new KGAT_ token style) after user exposed a live token in chat

Work Log:
- User pasted a live KGAT_ token into chat; advised immediate revocation (kaggle.com -> Settings -> API -> Expire Token) and that no token ever needs to be sent to anyone
- Found compatibility gap: pati_workers/kaggle_worker.py only accepted classic kaggle.json, but Kaggle's 2026 site issues new-style KGAT_ tokens
- Upgraded kaggle_worker.py: kaggle_credentials() detects 3 forms in order (KAGGLE_API_TOKEN env -> ~/.kaggle/access_token -> ~/.kaggle/kaggle.json); cli_env() forwards token to all kaggle CLI subprocesses; _kaggle_user() resolves username from kaggle.json -> KAGGLE_USERNAME env -> `kaggle config view` (cached) -> neutral fallback
- Updated docs/KAGGLE_WORKER.md + docs/INSTALL.md with Windows PowerShell and Linux setup for both token styles
- Added tests/test_kaggle_credentials.py (8 tests: absence reason, no CLI, env var, token file, classic json, env precedence, username fallback, register style report; no real secrets used)
- Regression: 54 tests pass (46 + 8) in 14.04s
- Rebuilt /home/z/my-project/download/PATI-zero-cost-infrastructure.zip (162 files)

Stage Summary:
- PATI now accepts both official Kaggle token styles; user can paste the NEW token into a local file instead of juggling kaggle.json
- Deliverable zip updated; token exposure incident handled with revocation guidance

---
Task ID: 16
Agent: main (Super Z)
Task: Build web+mobile dashboard as installable PWA (iOS/Android), full site-hygiene checklist, QA, docs

Work Log:
- User approved dashboard build + "app for both iOS and Android" + pasted a generic marketing-site checklist
- Decided PWA over native apps (Apple $99/yr + Google $25 violate FREE_FIRST) - installable from the browser on both platforms
- Generated PWA assets via Pillow (scripts/gen_dashboard_assets.py): icon-192/512, maskable-512, apple-touch-icon, favicon-64+svg, 1200x630 OG share image, avatar-default
- Built pati_api/webapp.py (~1000 lines): page shell (unique titles, meta descriptions, canonical, OG/Twitter meta, JSON-LD), dashboard (above-fold CTA + 4 quick chips + token connect, live system stats, jobs w/ stage progress bars + cancel, artifact gallery with authenticated blob media, response-time promise strip, proven-flows section, owner photo slot, local visit counter), FAQ (10 Qs + FAQPage schema), privacy page, thank-you page (wired to real submissions), custom 404, offline page, robots.txt (disallow-all by intent), sitemap.xml, llms.txt, manifest.webmanifest, sw.js (offline shell; API never cached)
- Wired routes in pati_api/app.py; SoftwareApplication JSON-LD with price 0 replaces "local business schema"; removed obsolete status_page.py; added PACKAGE_DIR to config
- Tests: tests/test_dashboard.py (15 checks); fixed test_visit_counter (module reload polluted session) to use live server; 69 passed total
- Bugs found by QA and fixed: JS referenced removed #stUptime element (threw -> "Offline"); owner-photo 404 logged console error (now serves placeholder avatar); llms.txt/footer pointed to wrong docs URL
- Playwright QA (scripts/qa_dashboard.py): crawled every route (18 paths) + custom 404; connected with real bootstrap token through the UI, submitted a job, verified thank-you redirect + live job list; 0 console errors, 0 warnings; desktop + phone screenshots
- Docs: docs/WEB_DASHBOARD.md (incl. honest checklist coverage table), README doc map, INSTALL.md section 5b (PWA install steps)
- Rebuilt zip: 171 files; final suite 69 passed in 14.45s

Stage Summary:
- PATI now ships a phone-first installable dashboard PWA with full site hygiene, zero third-party requests, and honest adaptations (no GA -> local counter; no team photos -> owner photo slot; SoftwareApplication schema; robots disallow-all)
- Deliverables: updated zip + 3 screenshots in download/

---
Task ID: 17
Agent: main (Super Z)
Task: Rebrand to DeYoung (white/red/black), owner-only /admin panel, free-signup payments (local + international)

Work Log:
- Interpreted brief: rename brand to DeYoung, palette white/red/black (#FFF/#DC2626/#0A0A0A), owner-only admin, photo upload for owner picture (sent later), free-to-signup payment that works local + international, site is public
- Prisma schema: Admin, Settings (single row incl. paymentProvider/keys/bank details/currency/socials/SEO), Photo, Service, Booking, Message, Testimonial, Faq; db pushed + seeded (4 services, 6 gallery placeholders, 3 reviews, 6 FAQs)
- Auth (src/lib/auth.ts): node:crypto scrypt password hashing + HMAC-signed session cookie (7d, httpOnly), per-install secret in db/.auth-secret; default owner admin@deyoung.site / deyoung123 with forced-change banner
- API: /api/auth/* (login/logout/me/change-password), /api/home (aggregated public), /api/settings (GET public-safe / PUT admin), /api/bookings (+[id] patch/delete, +[id]/verify server-side Paystack/Flutterwave verification), /api/contact, /api/photos|services|testimonials|faqs CRUD, /api/messages, /api/upload (multipart -> public/uploads), /api/overview stats, /api/admin/payments-meta + full-settings
- Frontend single-page (only / route, hash views): home (black hero + DY photo card, services, gallery lightbox, about, testimonials, FAQ accordion, contact), #book checkout (manual bank/mobile-money, Paystack inline, Flutterwave v3, PayPal buttons, Stripe payment link), #privacy, #thanks, #admin (9 tabs: Overview, Bookings=customers, Messages, Photos, Services, Reviews&FAQ, Payments, Site&Profile, Security)
- Brand assets via scripts/gen_deyoung_assets.py (avatar, gallery placeholders, OG 1200x630, PWA icons, favicon, pay-methods strip); manifest.webmanifest + sitemap.xml + robots.txt; layout metadata (title template, OG/Twitter, canonical, metadataBase, JSON-LD LocalBusiness); sticky mobile CTA bar with safe-area
- Fix: Turbopack served stale globals.css (brand vars empty -> invisible white-on-white hero); content change forced rebuild, re-verified
- E2E agent-browser: home desktop+mobile screenshots, booking flow (service select -> details -> manual pay -> thank-you), admin login -> overview stats -> booking marked paid (persisted: revenue $120) -> payments tab (provider cards + signup links + key fields), contact form -> admin inbox, upload API -> served at /uploads, settings PUT; 0 console errors, 0 page errors, eslint clean
- Screenshots: download/deyoung-home.png, deyoung-mobile.png, deyoung-checkout.png, deyoung-admin.png, deyoung-admin-payments.png

Stage Summary:
- DeYoung site is live on /: public booking site + owner-only admin panel, all content owner-editable (name, photo, gallery, services, prices, reviews, FAQ, contact, socials, payment method)
- Payments: default manual (bank/mobile money, zero signup, works today); one-click free signups for Paystack/Flutterwave (local + international), PayPal, Stripe link; server-side verification when secret key provided
- Owner credentials: admin@deyoung.site / deyoung123 (banner nags to change immediately); sample bookings/messages left in dashboard as demo data, deletable

---
Task ID: 18
Agent: main (Super Z)
Task: DeYoung as 60-second AI video service — Beginner/Pro/Elite monthly subscriptions, server-side tier limits, video request queue, capacity dashboard (answer-first per user request)

Work Log:
- Answered the user's question in chat BEFORE coding: confirmed business understanding (DeYoung = public AI video generation on PATI engine; differentiator = up to 60s single-pass vs industry ~15s cap), recommended tier matrix (Beginner $9/4 videos/15s/720p/watermark; Pro $29/20/60s/1080p/no watermark/commercial; Elite $79/60/60s/multi-scene/priority queue), and 8 scalability recommendations (queue-first, segment-and-stitch, dedup cache, GPU-minute metering, daily cap + waitlist, free GPU stacking, revenue-buys-GPU bridge, watermark trials)
- Prisma schema: Plan (code/price/limits/featuresJson/queuePriority), Subscription (period-based, provider, paymentRef), VideoRequest (prompt/seconds/resolution/status/queuePriority/dedupKey/fromCache/gpuMinutes), Settings.gpuMinutesDaily=240; db pushed, client regenerated
- Seed: 3 plans upserted with recommended limits + feature lists, 2 video FAQs (60s lengths, queue fairness), marketing copy refreshed to AI-video positioning (never overwrites owner edits)
- APIs: /api/plans (public GET active, admin PUT bulk-edit, owner GET sees all), /api/subscriptions (public create-pending, admin list), /api/subscriptions/[id] (activate N months / cancel / reactivate / delete cascades), /api/subscriptions/[id]/verify (server-side Paystack/Flutterwave verification auto-activates 1 month), /api/requests (public POST with server-side enforcement: active-sub required, seconds<=plan, resolution rank<=plan, audio gated, monthly quota 429, concurrent-render slots, dedup cache BEFORE concurrency so cache hits need no render slot; admin GET queue), /api/requests/[id] (public status by id+email match, admin start/deliver+gpuMinutes/fail/cancel/delete), /api/home now returns plans, /api/overview returns subscribers/MRR/queueDepth/GPU-minutes today vs budget, /api/upload accepts video/mp4|webm|mov up to 200MB
- Queue math: position = priority-desc then FIFO; ETA = estimated GPU-minutes (0.5 min/s at 720p, 1.0 at 1080p) / daily budget, rounded up — honest coarse estimate
- Frontend: PlansSection on home (3 tier cards, Pro highlighted, feature check/x lists, cache+queue explainer strip), #subscribe route (BookView subscription mode, unified Order checkout shared with bookings), #request view (submit form with length/resolution/audio pickers + result panel with request ID, ETA, usage; status checker with download link), header "Video Plans" link + Subscribe CTA, hero CTA "60-Second AI Video — See Plans", layout metadata retitled to AI-video positioning
- Admin: new tabs Plans (every limit editable incl. feature list syntax "- line = excluded"), Subscribers (activate months/cancel/reactivate/delete), Video Queue (start render, upload result file, GPU-min input, deliver, cancel; cache-hit badge); Overview cards now subscription revenue/active subs/queue depth + Today's Render Capacity progress bar (0/240 GPU-min)
- Bugs found by QA and fixed: isAdmin imported from @/lib/api (it lives in @/lib/auth); Turbopack stale-cache poisoned shared API chunks after new routes were added mid-session (2nd occurrence) — fixed by killing server + rm -rf .next + restart; dedup-cache check ordered before concurrent-limit so instant cache delivery works while a render is queued
- QA: scripts/smoke_subs.py — 32/32 checks across 14 stages (pending-sub rejection, tier enforcement 60s/1080p/audio, queue position+ETA+usage, concurrent limit, start/render/deliver, video upload+serving, public status, dedup cache hit, quota exhaustion 429, plans PUT live-edit + revert, 401 guards, overview stats, self-cleanup); UI E2E via agent-browser: subscribe→manual pay stage→activate→request "Queued — position 1"→admin delivers→status READY with download; 0 page errors; lint clean; mobile 390px screenshot
- Screenshots: download/deyoung-plans.png, deyoung-checkout-sub.png, deyoung-request.png, deyoung-admin-overview.png, deyoung-admin-plans.png, deyoung-admin-subs.png, deyoung-admin-queue.png, deyoung-mobile-plans.png

Stage Summary:
- DeYoung now sells the user's 60-second single-pass video capability as Beginner/Pro/Elite monthly subscriptions with every limit owner-editable from /admin, enforced server-side (browser never trusted)
- Queue-first delivery with honest ETA + capacity bar implements the scalability recommendations; dedup cache means repeat renders cost zero GPU
- All existing payment rails (manual/Paystack/Flutterwave/PayPal/Stripe) work for subscriptions via the same checkout; owner login admin@deyoung.site / deyoung123
- 32/32 smoke checks green; demo data (1 subscriber, 1 delivered request) left in dashboard as examples, deletable

---
Task ID: 22
Agent: main (Super Z)
Task: Regenerate the actual DeYoung 60s film (sandbox was reset — all video assets lost), rebuild social cards with mobile+web device mockups, push project to github.com/bluzsammy-png/Deyoung

Work Log:
- Discovered workspace reset: no video/campaign/social assets; site code + git repo intact (no remote)
- Rebuilt toolchain: brand mark (Playwright SVG->PNG), fonts (Archivo var, Archivo Black, JetBrains Mono), film stills (amara/kojo/duo/silk via z-ai image)
- Video: z-ai video SDK, 8 scenes (3 i2v character scenes quality 10s, 5 t2v speed 5s) + 5s ffmpeg end card = 60s; rolling submission to respect ~429 rate limit (film_poll.mjs keeps 2 in flight)
- Assembly: assemble_film.py — normalize 1280x720, grade/vignette, burned dialogue + speaker tags, end card w/ mark, aevalsrc drone score, master + web (crf27 hqdn3d faststart)
- Social: Playwright site screenshots (desktop+mobile) -> social_posts.py v2 composites laptop+phone mockups into 7 cards (download/social/) — every card shows mobile + web experience
- Site: hero.tsx gained "Watch the 60-second film" video band (web mp4 + poster); .gitignore excludes campaign/download/upload/db; README.md added

Stage Summary (completed this session, 17:13–18:05 UTC):
- Film: resumed rate-limited scene pipeline in foreground poll runs (background node gets killed); s05–s08 downloaded by 17:43 (8/8); assemble_film.py completed (norms + endcard + score + 69MB master); web encode: 1280x720 h264+aac crf27 hqdn3d faststart -> public/video/deyoung-film-web.mp4 (16.1MB, exactly 60.000s, moov-first verified)
- QA: HTTP range request on /video/deyoung-film-web.mp4 returns 206 video/mp4; poster 200; cards visually verified (mobile+web mockups present on every card)
- Git: untracked .env (DATABASE_URL path only) + explicit .env ignore; chose clean-history strategy (old history contained auto-committed db/.auth-secret + custom.db): orphan branch -> single commit 2a370be "DeYoung — AI Video Studio" (337 files) -> pushed to github.com/bluzsammy-png/Deyoung main (PAT used one-shot in push URL, no remote saved, no credential helper)
- Pushed tree verified: film + poster + README present; 0 db/.env/download/campaign paths
- SECURITY: GitHub PAT exposed in chat — user must rotate/revoke immediately (github.com/settings/tokens), same for the Kaggle token shared earlier

---
Task ID: 23
Agent: main (Super Z)
Task: Fix Railway (Railpack) deploy failure — build expected prisma/schema.postgres.prisma + deploy/start.sh; wire app to Supabase Postgres

Work Log:
- Diagnosed Railway log: custom build command `prisma generate --schema prisma/schema.postgres.prisma && next build && cp …` failed at missing schema file; start command `sh deploy/start.sh` referenced a nonexistent file; both configured in the Railway dashboard
- Created prisma/schema.postgres.prisma (sed-transform of schema.prisma: provider postgresql, models verified byte-identical)
- Created deploy/start.sh: idempotent `prisma db push --schema … --skip-generate` + `node scripts/seed.ts` (Node 24 native TS) non-fatal on boot, then exec node .next/standalone/server.js with HOSTNAME=0.0.0.0 + PORT
- next.config.ts: added outputFileTracingIncludes (.prisma + @prisma/client) so the query engine ships in the standalone bundle
- Supabase Postgres (user-provided): password contains `#` which MUST be URL-encoded %23; `prisma db push` succeeded (8.43s, all tables created); generated postgres client, seeded live DB (admin + 3 plans + 4 services + 6 photos + 3 testimonials + 8 FAQs), regenerated sqlite client, dev server restarted (200)
- Committed e994a2a and pushed to GitHub with user's NEW PAT (ghp_FLax…; old ghp_7qn9… presumably rotated) → Railway auto-redeploy triggered
- Pushed tree verified to contain the 3 new/changed files; no remote saved (no PAT persisted)

Stage Summary:
- Railway build will now find schema.postgres.prisma; boot will db push + seed then serve standalone on $PORT
- User must set DATABASE_URL in Railway: postgresql://postgres.REDACTED-C6-OLD-PROJ-REF:REDACTED-C6-DB-PASSWORD@aws-0-eu-central-1.pooler.supabase.com:5432/postgres?sslmode=require
- SECURITY: new GitHub PAT + Supabase password + QuantEdge token all exposed in chat — advise rotating Supabase db password & revoking tokens after setup
