# INSTALL — Installation & Setup Guide

PATI is designed **Windows-first** (per the product decision: Windows PC, no
local GPU) but runs anywhere Python 3.11+ runs. Every step below is $0 — no
credit card, no paid tier, no trial.

## 0. Prerequisites

| Requirement | Minimum | Check |
|-------------|---------|-------|
| OS | Windows 10/11 (macOS/Linux supported) | — |
| Python | 3.11+ | `python --version` |
| Disk | ~500 MB for PATI + model caches | — |
| RAM | 4 GB (control plane is lightweight) | — |
| Network | Internet for Kaggle GPU + tunnels | — |
| Git (optional) | any recent | `git --version` |

Optional free extras:

- **Cloudflare Tunnel** (`winget install --id Cloudflare.cloudflared`) — free
  remote access to your control plane, no port forwarding, no credit card.
- **Kaggle account** — free GPU (~30 h/week). Create an API token at
  kaggle.com → Settings → API → Create New Token; save it as
  `~/.kaggle/access_token` (new style) or `~/.kaggle/kaggle.json` (classic).

## 1. One-command install (Windows)

```powershell
# from the repo root
Set-ExecutionPolicy -Scope Process Bypass
.\installer\install.ps1
```

The installer:

1. Verifies prerequisites (Python version, disk space).
2. Creates an isolated virtualenv `.venv` in the repo.
3. `pip install -e .` — installs `pati`, `pati-server`, `pati-agent` CLIs.
4. Starts the control plane on `http://127.0.0.1:8000`.
5. Prints a **pairing code** (single-use, 10-minute TTL).
6. Launches the **12-step Local Agent setup wizard**.

## 2. The 12-step wizard (Local Agent)

Run automatically by the installer, or manually with `pati-agent setup`:

| Step | What it does |
|------|--------------|
| 1 | Asks for the control plane URL (default `http://127.0.0.1:8000`) |
| 2 | Asks for the pairing code (from `pati admin-pair`) |
| 3 | Registers this computer as a worker with a stable worker id |
| 4 | Receives a scoped worker token (bound to this worker id) |
| 5 | Asks for a friendly PC name |
| 6 | Asks for **authorized folders** (the only paths PATI may touch) |
| 7 | Asks for permissions — dangerous ones (delete/exec/run-models) default OFF |
| 8 | Detects hardware (CPU/RAM/disk, GPU presence) |
| 9 | Writes the local policy file (`policy.json`) |
| 10 | Runs a self-test (path guard, fs ops, exec sandbox) |
| 11 | Verifies round-trip with the control plane (claim → result) |
| 12 | Offers autostart registration (Task Scheduler / systemd / launchd) |

Non-interactive (CI/containers):

```bash
pati-agent setup --server http://127.0.0.1:8000 --code ABC123 \
  --roots "C:/Users/me/PATIWorkspace" --non-interactive
```

## 3. Manual install (any OS)

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -e .

pati-server                        # control plane on 127.0.0.1:8000
pati admin-pair                    # pairing code for a new computer
pati-agent setup                   # wizard on the target computer
pati-agent run                     # the agent loop (pull-based)
```

## 4. Verify the installation

```bash
# health (no token needed)
curl http://127.0.0.1:8000/health
# → {"status":"ok","max_spend":0,"free_only":true,...}

# self-check of the local installation
pati-agent doctor                  # env, policy, disk, server reachability

# end-to-end smoke test
export PATI_SERVER=http://127.0.0.1:8000
export PATI_TOKEN=<client token>
pati submit "Create a folder called YouTube Project 01 in my workspace" --wait
```

Full proofs: `python examples/e2e_demo.py` (disk flow) and
`python examples/e2e_remote_gpu.py` (free-GPU pipeline; degrades to
`RESOURCE_UNAVAILABLE` if no Kaggle token — never a paid fallback).

## 5. Free remote access (Cloudflare Tunnel)

On the PC running the control plane:

```powershell
winget install --id Cloudflare.cloudflared
.\installer\enable-tunnel.ps1
```

The script:

1. Offers **Quick Tunnel** (`cloudflared tunnel --url http://localhost:8000`)
   — zero-account, zero-config, ephemeral URL; or a **named tunnel** (free
   Cloudflare account) with a stable hostname and autostart.
2. Prints the public `https://…trycloudflare.com` URL to use as `PATI_SERVER`
   on remote devices.
3. Reminds you that **tokens, not the tunnel, are the security boundary** —
   keep `PATI_TOKEN` secret; all routes stay bearer-authenticated.

## 5b. Install the dashboard as a phone app (PWA, $0)

Open the tunnel URL on your phone, paste your token into the Connect box once,
then:

- **Android (Chrome/Edge):** tap **Install as app** (or menu → *Add to Home
  screen*).
- **iOS (Safari):** Share → **Add to Home Screen**.

PATI launches full-screen with its own icon — no app store, no fees (native
stores would cost $99/yr + $25, which violates the $0 policy). Custom domain
instructions: `docs/WEB_DASHBOARD.md`.

## 6. Free GPU (Kaggle)

1. kaggle.com → profile picture → Settings → API → **Create New Token**.
2. Save the token (Windows PowerShell):

   ```powershell
   New-Item -ItemType Directory -Force "$env:USERPROFILE\.kaggle" | Out-Null
   Set-Content -Path "$env:USERPROFILE\.kaggle\access_token" -Value "PASTE_NEW_TOKEN_HERE" -NoNewline
   setx KAGGLE_USERNAME "your-kaggle-username"   # optional, resolves kernel slugs faster
   ```

   Classic `kaggle.json` at `C:\Users\<you>\.kaggle\kaggle.json` also works.
3. PATI's quota manager budgets GPU minutes locally (default **240 min/day**;
   tune in `docs/QUOTA_MANAGER.md`).
4. Submit jobs normally: `pati submit "generate an image of …"` — the router
   picks the Kaggle worker when a GPU capability is requested.

Without any token the Kaggle worker reports `unavailable` at registration
and GPU jobs park in `WAITING_FOR_RESOURCE` until it appears.

## 7. Autostart as a service

| OS | Mechanism | File |
|----|-----------|------|
| Windows | Task Scheduler (set up by wizard step 12) | — |
| Linux | systemd user service | `installer/pati-agent.service` |
| macOS | launchd | `installer/com.pati.agent.plist` |

```bash
# Linux example
cp installer/pati-agent.service ~/.config/systemd/user/
systemctl --user enable --now pati-agent
```

## 8. Uninstall

```powershell
.\installer\uninstall.ps1     # Windows
./installer/uninstall.sh      # macOS/Linux
```

Removes the venv, services, scheduled tasks and (optionally, after a prompt)
the SQLite database and artifact store. The audit log is preserved unless you
explicitly confirm deletion.
