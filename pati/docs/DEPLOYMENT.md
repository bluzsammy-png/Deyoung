# DEPLOYMENT — Deployment Topologies

PATI ships as a single-process control plane plus pull-based workers. That
makes deployment a matter of *where* you put two things: the API process and
the agent process(es). All topologies below are $0.

## 1. Topology A — Single PC (default, recommended start)

```
[ Your Windows PC ]
  ├─ pati-server (control plane)      127.0.0.1:8000
  ├─ pati-agent  (local worker)       loopback long-poll
  └─ artifacts/ + pati.db             local disk
```

- Everything on one machine, loopback only, no exposure.
- GPU jobs go out to Kaggle via the official free API; results come back as
  artifacts the local agent saves into authorized folders.
- Install: `installer/install.ps1`. This is what the E2E examples assume.

**When:** personal use, one computer, maximum security posture.

## 2. Topology B — Single PC + remote devices (free tunnel)

```
[Phone/laptop elsewhere]                [ Your PC ]
  PatiClient ── https://<tunnel> ──► cloudflared ──► pati-server ──► pati-agent
```

- `installer/enable-tunnel.ps1` offers Quick Tunnel (ephemeral URL, zero
  account) or a named tunnel (free account, stable hostname, autostart).
- The tunnel is transport only; **every route still requires a bearer
  token**, workers are id-bound, and scopes apply. Treat the tunnel URL as
  semi-public and the token as the actual secret.
- Hardening checklist for this topology (docs/SECURITY.md §Remote):
  1. Use a named tunnel + your own hostname so you can rotate it.
  2. Mint per-device client tokens (`pati admin token-create --role client`).
  3. Keep admin tokens off phones; admin scope on the PC only.
  4. Review the central audit trail after first-time device access.

**When:** you want to drive PATI from anywhere without paying for a VPS.

## 3. Topology C — PC + second machine as extra worker

```
[ PC: control plane ] ◄── long-poll ── [ Laptop/Raspberry Pi: pati-agent ]
```

- Run `pati admin-pair` on the PC, run `pati-agent setup` on the second
  machine with the PC's URL (via LAN IP or tunnel).
- The new worker's capabilities (disk roots, hardware) are its own; jobs
  route only to workers that offer the requested capability.
- Nice for: dedicated "render box," a Mac with better local TTS, or a NAS
  with big authorized storage.

## 4. Topology D — Container worker for isolation-hungry jobs

```
[ PC ]
  ├─ pati-server
  ├─ pati-agent (authorized folders)
  └─ Docker: container-worker (disposable sandbox)
```

- The container worker registers like any worker and claims jobs tagged for
  its capabilities. Ephemeral filesystem = strong isolation for sketchy
  scripts; artifacts still flow back through the artifact store.
- Docker Desktop on Windows is free for personal use; the worker itself is
  plain Python.

**When:** you want `EXECUTE_COMMANDS`-class work isolated from your real
filesystem even beyond the path guard and rlimits.

## 5. Topology E — Kaggle as the compute plane

```
[ PC: control plane ] ── official Kaggle API ──► [ Kaggle kernel: free GPU ]
        ▲                                              │
        └────────── artifacts (download) ◄─────────────┘
```

- Kaggle is *not* a long-running worker process; the Kaggle worker module
  pushes a kernel job, Kaggle's scheduler runs it on free GPUs, and outputs
  are pulled back as artifacts. The quota manager treats Kaggle GPU minutes
  as a finite local budget (default 240 min/day).
- Registration is capability-driven: with a valid `kaggle.json` the worker
  advertises GPU capabilities (image, video, TTS, Whisper, open-weights LLMs
  per `docs/MODEL_REGISTRY.md`); without it, it registers `unavailable`.

**When:** any GPU capability at all. This is the only compute plane PATI
ships with that can produce images/video/music at scale for $0.

## 6. Choosing a topology

| Need | Topology |
|------|----------|
| Just me, just this PC | A |
| Drive PATI from phone / travel | B |
| Spare machine with storage or different OS | C |
| Run untrusted scripts more safely | D |
| Images / video / voice / music / LLMs | E (with A) |

Topologies compose: A+B+C+D+E simultaneously is the full personal setup and
still costs nothing but electricity and disk.

## 7. Production hygiene (even at home)

1. **Backups:** copy `pati.db` and `artifacts/` to a second disk (Windows
   Task Scheduler weekly). Restore is documented in FAILURE_RECOVERY §4.
2. **Updates:** `git pull && pip install -e . && pati-server` restart; run
   `python -m pytest tests -q` before restarting a healthy install.
3. **Secrets:** only `PATI_TOKEN` values and `kaggle.json` exist; store them
   in the OS credential store if you like, never in the repo folder.
4. **Monitoring:** `GET /health`, `GET /workers`, agent console + audit log.
   The status page (control plane root) is the one-glance dashboard.
5. **Resource bounds:** the control plane is a FastAPI/SQLite app — 4 GB RAM
   machines run it comfortably; artifact retention policy keeps disk bounded
   (docs/ARTIFACT_SPEC.md).

## 8. Anti-goals

- No Kubernetes, no service mesh, no paid cloud. PATI's control plane is one
  process by design; scaling it into a cluster would violate the product's
  core promise (personal, $0, inspectable).
- No multi-user hardening for the public internet. Topology B is fine for one
  person's devices; MULTI_TENANCY.md describes the deliberate boundaries.
