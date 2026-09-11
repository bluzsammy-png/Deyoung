#!/usr/bin/env python3
"""Free GPU Registration Tracker - combines research shortlist + fleet + runbook.
v2 (Task 67): Baidu + ModelScope statuses updated after live onboarding canary.
v3 (Task 68): vault unsealed+re-sealed with owner passphrase; Baidu -> Onboarded;
ModelScope still 401 (re-copy pending); Kaggle mirror pushed, round-trip pending rate-limit."""
import sys, os
XLSX_SKILL_DIR = "/home/z/my-project/skills/xlsx"
for sub in [XLSX_SKILL_DIR, os.path.join(XLSX_SKILL_DIR, "templates")]:
    if sub not in sys.path:
        sys.path.insert(0, sub)
from base import *  # design tokens + style factories
from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import PatternFill, Font

OUT = "/home/z/my-project/download/Free_GPU_Registration_Tracker.xlsx"

wb = Workbook()

def build_table(ws, title, headers, rows, freeze="C5"):
    last_col = len(headers) + 1
    setup_sheet(ws, title=title, last_col=last_col)
    for c, h in enumerate(headers, start=2):
        ws.cell(row=4, column=c, value=h)
    style_header_row(ws, row_num=4, col_start=2, col_end=last_col)
    for i, row in enumerate(rows):
        rn = 5 + i
        for c, v in enumerate(row, start=2):
            ws.cell(row=rn, column=c, value=v)
        style_data_row(ws, row_num=rn, col_start=2, col_end=last_col, row_index=i)
    ws.freeze_panes = freeze
    auto_fit_columns(ws, min_width=8, max_width=42, header_row=4, data_start_row=5)
    return 5 + len(rows) - 1

# ---------------- Sheet 1: Register Now ----------------
ws1 = wb.active
ws1.title = "Register Now"
h1 = ["Priority", "Provider", "Signup URL", "What You Get at $0", "Renewal",
      "Verification Needed", "First Role in Fleet", "Credential to Hand Back", "Status"]
rows1 = [
    ["P1", "Modal", "https://modal.com/signup",
     "$30/mo Starter credits ($5/mo without card); serverless T4/L4/A10/L40S/A100, per-second billing, 10 concurrent GPUs",
     "Monthly", "Email + optional card (raises $5 to $30)", "Nightly inference / eval rhythm jobs",
     "API token (modal token new)", "To register"],
    ["P2", "ModelScope (Alibaba)", "https://www.modelscope.cn",
     "36-hr welcome A10 24GB + recurring free windows (~8 hrs/day, community-reported); AMD incentive program through Dec 2026",
     "Recurring windows", "Regional signup; Aliyun binding for some routes", "24GB VRAM lane: LoRA, 13B-class FP16",
     "Access token", "Token handed off"],
    ["P3", "Baidu AI Studio", "https://aistudio.baidu.com",
     "~8 compute points daily = ~16 hrs/day V100-16GB; A100 grants via programs; + LLM API (ernie) with the same account",
     "Daily", "Chinese phone verification flow", "V100 bulk training lane + ernie inference",
     "Access token", "Onboarded"],
    ["P4", "Google TPU Research Cloud", "https://research.google/tpu",
     "Cloud TPU v4 / v5e pod slices on 30-day rolling projects",
     "Application + renewal", "Research justification; publication intent", "Quarterly heavy training (JAX/XLA)",
     "GCP project + credentials", "To register"],
    ["P5", "Intel Tiber AI Cloud", "https://cloud.intel.com",
     "Free evaluation: Gaudi 2/3, Data Center GPU Max, Arc; JupyterLab labs",
     "Session-bounded", "Intel account only", "Non-CUDA diversification / OpenVINO serving",
     "Intel account token", "To register"],
    ["P6", "Saturn Cloud", "https://saturncloud.io",
     "~30 compute hrs/month incl. GPU pools, no card; cleanest quota in the West",
     "Monthly", "No card", "Overflow lane when weekly planes drain mid-cycle",
     "API token", "To register"],
    ["P7", "Akash Console", "https://console.akash.network",
     "$100 one-shot trial credits; decentralized marketplace with H100/A100 rentals",
     "One-shot", "Email + card verification", "Big-bang hardware burst",
     "Wallet / deploy key", "To register"],
    ["P8", "Paperspace Gradient (DigitalOcean)", "https://www.paperspace.com",
     "Standing free-GPU class M4000 8GB, ~6 hr sessions (capacity-starved, bonus-only)",
     "Standing (eroding)", "No card", "Last-resort burst; lowest survival outlook in Tier 1",
     "API token", "To register"],
    ["P9", "OpenBayes", "https://openbayes.com",
     "~4 GPU-hrs RTX 4090 welcome + 50GB storage (one-shot); catalog up to RTX 5090-class",
     "One-shot", "Regional signup", "Top-consumer-GPU burst",
     "API token", "To register"],
    ["P10", "OpenI (Pengcheng)", "https://openi.pcl.ac.cn",
     "A100-class GPUs + domestic NPUs tied to public open-source activity; 50 card-hour promos",
     "Project / point-based", "Account + public repo activity", "A100 burst for OSS work",
     "Token", "To register"],
    ["P11", "GPU-Grants (Prime Intellect)", "https://github.com/eric-prog/GPU-Grants",
     "$500 to $100,000 project compute credits for innovative GPU projects",
     "Application", "Serious open GPU project", "Heavy-training capital",
     "n/a (grant program)", "To register"],
    ["P12", "RunPod referrals", "https://www.runpod.io",
     "$5-$500 randomized referral credits; cheap 4090 community cloud",
     "Per referral event", "No", "Credit top-up lane",
     "API key", "To register"],
    ["P13", "Azure for Students", "https://azure.microsoft.com/free/students",
     "$100/year Azure credits via GitHub Student Developer Pack; NC-series T4 bursts",
     "Annual re-verify", "Student status", "Student-only burst",
     "Service principal", "To register"],
]
last1 = build_table(ws1, "Free GPU Registration Tracker - Register In This Order (verified Sep 2026)", h1, rows1, freeze="D5")

dv = DataValidation(type="list",
    formula1='"To register,Registering,Registered,Token handed off,Onboarded,Dead"',
    allow_blank=False, showDropDown=False)
ws1.add_data_validation(dv)
dv.add(f"J5:J{last1}")

green_fill = PatternFill('solid', fgColor='E8F5E9'); green_font = Font(name=FONT_NAME, color=ACCENT_POSITIVE)
amber_fill = PatternFill('solid', fgColor='FEF9E7'); amber_font = Font(name=FONT_NAME, color=ACCENT_WARNING)
red_fill = PatternFill('solid', fgColor='FDEDEC'); red_font = Font(name=FONT_NAME, color=ACCENT_NEGATIVE)
rng = f"J5:J{last1}"
ws1.conditional_formatting.add(rng, FormulaRule(formula=['$J5="Onboarded"'], fill=green_fill, font=green_font))
ws1.conditional_formatting.add(rng, FormulaRule(formula=['OR($J5="Registering",$J5="Token handed off")'], fill=amber_fill, font=amber_font))
ws1.conditional_formatting.add(rng, FormulaRule(formula=['$J5="Dead"'], fill=red_fill, font=red_font))

n1 = last1 + 2
ws1.cell(row=n1, column=2, value="Registered or onboarded:")
ws1.cell(row=n1, column=2).font = font_caption()
c = ws1.cell(row=n1, column=3, value=f'=COUNTIF(J5:J{last1},"Registered")+COUNTIF(J5:J{last1},"Onboarded")+COUNTIF(J5:J{last1},"Token handed off")')
c.font = font_body()
ws1.cell(row=n1 + 1, column=2, value="Total providers tracked:")
ws1.cell(row=n1 + 1, column=2).font = font_caption()
c2 = ws1.cell(row=n1 + 1, column=3, value=f"=COUNTA(C5:C{last1})")
c2.font = font_body()

n3 = n1 + 3
ws1.cell(row=n3, column=2, value="Task 70 status: Baidu = Onboarded (canary PASS x3, Actions-verified). ModelScope = TWO well-formed tokens both 401 with /models public-200 -> account-side API-Inference activation required (enable on a model page / phone verification / Aliyun binding). New token ms-a3d... propagated fleet-wide (vault re-sealed round-trip PASS, Actions secret HTTP 204, GitHub mirror synced) - the 5-min Actions doctor cron will flip to VALID automatically once activated. Kaggle vault re-created NEW (private); round-trip final check deferred (rate limit).")
ws1.cell(row=n3, column=2).font = font_caption()

# ---------------- Sheet 2: Existing Fleet ----------------
ws2 = wb.create_sheet("Existing Fleet")
h2 = ["Plane", "Accounts", "Free Quota", "Verified Status (Sep 11, 2026)", "Integration Surface"]
rows2 = [
    ["Lightning AI", "1 studio (deyoung-h3)",
     "15 credits/mo = ~80 spot GPU-hrs or ~22 on-demand T4-hrs",
     "Balance -0.319; studio stopped; doctor gates on MIN_START_BALANCE=0.85",
     "LIGHTNING_API_KEY (Actions secret) + lightning_tokens.json"],
    ["Kaggle", "6 accounts / 8 KGATs (k2,k4=bittrexminingltd; k3,k8=teslaprime)",
     "~30 GPU-hrs/week each + ~20 TPU-hrs/week",
     "All 6 accounts quota-exhausted this week; rolling resets; auto-resume armed",
     "KAGGLE_API_TOKEN + kaggle_tokens.json"],
    ["Hugging Face", "4 fine-grained tokens (deyoungsltd, bittrexminingltd, bluzsammy, jimmmfg)",
     "ZeroGPU ~5 min/day free + model hosting",
     "4/4 tokens valid; Spaces hosting 402 on free tier; role = weights + mirror + reserve",
     "hf_tokens.json + vault.enc + private mirror"],
    ["Baidu AI Studio (NEW)", "1 account (baidu-1)",
     "LLM API live (ernie); notebook points = separate daily grant",
     "ONBOARDED 2026-09-12: canary PASS x2, doctor 0-burn probe, in vault.enc + Kaggle mirror",
     "baidu_tokens.json + vault.enc (re-sealed Task 68)"],
    ["ModelScope (NEW)", "1 account (ms-1)",
     "API-Inference free tier + A10 notebook quota (separate)",
     "401 despite 2 valid-format tokens -> ACTIVATION required on account (API-Inference enable / Aliyun binding); token ms-a3d... propagated fleet-wide 2026-09-11",
     "modelscope_tokens.json + vault.enc + Actions secret (all updated)"],
]
last2 = build_table(ws2, "Fleet Planes (existing + new, vault / doctor / mirror status)", h2, rows2)
n2 = last2 + 2
ws2.cell(row=n2, column=2, value="New registrations join the same 4-step onboarding: vault ingest -> doctor probe -> mirror seed -> live canary.")
ws2.cell(row=n2, column=2).font = font_caption()

# ---------------- Sheet 3: Onboarding Runbook ----------------
ws3 = wb.create_sheet("Onboarding Runbook")
h3 = ["Step", "Action", "Owner", "Tooling", "Done When"]
rows3 = [
    [1, "Register the account (email, phone, captcha, 2FA)", "YOU - human-only, browser",
     "Signup URL from Register Now sheet", "Login works"],
    [2, "Generate the API credential", "YOU - provider console",
     "API tokens / keys page of the platform", "Token string exists"],
    [3, "Hand the token to the fleet", "YOU - paste in chat",
     "Vault ingest", "Entry in vault.enc + fleet secrets json"],
    [4, "Doctor probe (validity + quota read)", "FLEET", "fleet_doctor_actions.py",
     "Token-valid + quota evidence json"],
    [5, "Mirror seed", "FLEET", "vault_mirror_sync_63.sh",
     "Private mirror commit verified private"],
    [6, "Live canary job", "FLEET", "Per-plane canary runner",
     "Evidence json in brain/ + status flips to Onboarded"],
]
last3 = build_table(ws3, "Per-Provider Onboarding Runbook (same flow as the existing fleet)", h3, rows3)
n3 = last3 + 2
ws3.cell(row=n3, column=2, value="Guardrail: one real identity per platform per person. Farming multiplies ban risk and vendors respond by killing tiers - one legitimate account per provider is the durable play.")
ws3.cell(row=n3, column=2).font = font_caption()

# ---------------- Sheet 4: Tracking Repos ----------------
ws4 = wb.create_sheet("Tracking Repos")
h4 = ["Repo / List", "URL", "What It Tracks", "Notes"]
rows4 = [
    ["zszazi/Deep-learning-in-cloud", "https://github.com/zszazi/Deep-learning-in-cloud",
     "Curated list of deep-learning cloud providers incl. free tiers", "Long-lived; historical breadth"],
    ["eric-prog/GPU-Grants", "https://github.com/eric-prog/GPU-Grants",
     "Aggregated compute grant programs (Prime Intellect $500-$100k)", "Application-gated capital"],
    ["ARahim3/kaggle-tpu-lab", "https://github.com/ARahim3/kaggle-tpu-lab",
     "Kaggle TPU quota tooling (~20 TPU-hrs/wk, 9-hr cap)", "Active as of Sep 2026"],
    ["tensorpool/tensorpool", "https://github.com/tensorpool/tensorpool",
     "GPU CI beta: GitHub-triggered training runs", "Free beta minutes"],
    ["discdiver gist: DL cloud providers", "https://gist.github.com/discdiver/e4375fe287cb10d51a5bef6045f82d20",
     "Deep-learning cloud service provider gist", "Reference list"],
]
build_table(ws4, "GitHub Repos That Track Free GPU Compute", h4, rows4)

# ---------------- Sheet 5: Sources ----------------
ws5 = wb.create_sheet("Sources")
h5 = ["Source", "Class", "Key Fact", "Retrieved"]
rows5 = [
    ["lightning.ai/pricing", "[A]", "15 free credits/mo = ~80 interruptible GPU-hrs", "Sep 12, 2026"],
    ["kaggle.com/docs/efficient-gpu-usage", "[A]", "~30 GPU-hrs/week quota, weekly reset", "Sep 12, 2026"],
    ["huggingface.co (Spaces ZeroGPU docs)", "[A]", "ZeroGPU free for all users; PRO = 8x quota + priority", "Sep 12, 2026"],
    ["metacto.com HF pricing analysis", "[C]", "Free ZeroGPU ~3.5-5 min/day", "Sep 12, 2026"],
    ["modelscope.cn notebook intro (Jul 30, 2026)", "[A]", "Free-compute notebook routes; welcome quota", "Sep 12, 2026"],
    ["tianchi.aliyun.com ModelScope free resources", "[A]", "36-hr free single A10 via PAI-DSW", "Sep 12, 2026"],
    ["aistudio.baidu.com usage page", "[A]", "Daily 8 compute points = ~16 hrs V100-16GB", "Sep 12, 2026"],
    ["paperspace.com pricing + spheron.network comparison (Jul 23, 2026)", "[A/B]", "Free M4000 class alive; ~6-hr session cap", "Sep 12, 2026"],
    ["cloud.intel.com", "[A]", "Free eval access: Gaudi 2/3, GPU Max, Arc", "Sep 12, 2026"],
    ["saturncloud.io", "[A]", "~30 free compute hrs/month, no card", "Sep 12, 2026"],
    ["xraise.ai RunPod startup credits (Jul 22, 2026)", "[C]", "$5-$500 randomized referral credits", "Sep 12, 2026"],
    ["research.google/tpu; allocations.access-ci.org; nairrpilot.org", "[A]", "TRC / ACCESS / NAIRR eligibility gates", "Sep 12, 2026"],
    ["console.akash.network; docs.oracle.com; easecloud.io (Feb 26, 2026)", "[A/B]", "Akash $100 trial; OCI A10 not always-free ($300 trial route)", "Sep 12, 2026"],
]
last5 = build_table(ws5, "Verification Sources (deep study rebuildable on request)", h5, rows5)
n5 = last5 + 2
ws5.cell(row=n5, column=2, value="[A] vendor official / [B] dated third-party analysis / [C] community report. All retrieved Sep 12, 2026.")
ws5.cell(row=n5, column=2).font = font_caption()

# ---------------- Sheet 6: Review ----------------
ws6 = wb.create_sheet("Review")
ws6.sheet_properties.tabColor = "FFC000"
h6 = ["Check", "Expected", "Actual", "Status"]
rows6 = [
    ["Providers listed", 13, "=COUNTA('Register Now'!C5:C17)", '=IF(C5=D5,"PASS","FAIL")'],
    ["Status values all valid", 13,
     '=COUNTIF(\'Register Now\'!J5:J17,"To register")+COUNTIF(\'Register Now\'!J5:J17,"Registering")'
     '+COUNTIF(\'Register Now\'!J5:J17,"Registered")+COUNTIF(\'Register Now\'!J5:J17,"Token handed off")'
     '+COUNTIF(\'Register Now\'!J5:J17,"Onboarded")+COUNTIF(\'Register Now\'!J5:J17,"Dead")',
     '=IF(C6=D6,"PASS","FAIL")'],
    ["Runbook steps", 6, "=COUNTA('Onboarding Runbook'!C5:C10)", '=IF(C7=D7,"PASS","FAIL")'],
    ["Fleet planes", 5, "=COUNTA('Existing Fleet'!C5:C9)", '=IF(C8=D8,"PASS","FAIL")'],
]
build_table(ws6, "Cross-Validation Review", h6, rows6)

wb.properties.creator = "Z.ai"
wb.save(OUT)
print("saved:", OUT)
