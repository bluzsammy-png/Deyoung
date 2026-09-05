#!/usr/bin/env python3
"""
DeYoung DB-mode worker — the fleet path that does NOT depend on the site's
HTTP API. Railway's edge rate-limits datacenter IPs (Kaggle included), so
Kaggle GPU workers talk straight to the production Postgres:

  claim   — atomic single-statement UPDATE ... WHERE id = (SELECT ... FOR
            UPDATE SKIP LOCKED): a fleet of concurrent workers can never
            double-claim, on the DB's own guarantee.
  progress — plain UPDATE on the same VideoRequest rows the user panel reads,
            so the studio queue still shows live progress in the browser.
  deliver — the scene mp4 goes into the WorkerArtifact table (bytea) and the
            request row is marked done. The merge stage pulls artifacts out.
  fail    — honest failure with a reason, same as the HTTP plane.

Rendering, QA gate, film mode, local TTS: all reused from deyoung_worker.py
unchanged. Run with --renderer film exactly like the HTTP worker.

Usage:
  WORKER_DB_DSN='postgresql://worker_bot.<ref>:<pw>@host:5432/postgres?sslmode=require' \
      python3 deyoung_db_worker.py --renderer film --exit-idle --agent kaggle-gpu-a
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
import types
import uuid

import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import deyoung_worker as dw  # noqa: E402


def log(msg):
    print(f"[deyoung-dbworker {time.strftime('%H:%M:%S')}] {msg}", flush=True)


CLAIM_SQL = '''
UPDATE "VideoRequest" SET
  status = 'rendering', progress = 0, stage = 'claimed',
  notes = %(claim)s, "updatedAt" = now()
WHERE id = (
  SELECT id FROM "VideoRequest"
  WHERE status = 'queued'
  ORDER BY "queuePriority" DESC, "createdAt" ASC, id ASC
  LIMIT 1 FOR UPDATE SKIP LOCKED
)
RETURNING id, prompt, seconds, resolution, "withAudio", watermark,
          "queuePriority", model, voice, "refImageUrl", "createdAt"
'''

RECLAIM_SQL = '''
UPDATE "VideoRequest" SET status = 'queued', stage = '', progress = 0,
  notes = 'requeued: previous worker went silent', "updatedAt" = now()
WHERE status = 'rendering' AND "updatedAt" < now() - (%(stale)s)::interval
'''

PROGRESS_SQL = '''
UPDATE "VideoRequest" SET notes = %(note)s, progress = %(pct)s,
  stage = %(stage)s, "updatedAt" = now() WHERE id = %(id)s
'''

DELIVER_ARTIFACT_SQL = '''
INSERT INTO "WorkerArtifact" (id, "requestId", mime, bytes, size)
VALUES (%(id)s, %(rid)s, 'video/mp4', %(bytes)s, %(size)s)
'''

DELIVER_ROW_SQL = '''
UPDATE "VideoRequest" SET status = 'done', progress = 100, stage = 'delivered',
  "gpuMinutes" = %(gpu)s, "resultUrl" = %(url)s, notes = %(note)s, "updatedAt" = now()
WHERE id = %(id)s
'''

FAIL_SQL = '''
UPDATE "VideoRequest" SET status = 'failed', stage = 'failed',
  notes = %(note)s, "updatedAt" = now() WHERE id = %(id)s
'''


class DB:
    def __init__(self, dsn):
        self.dsn = dsn

    def conn(self):
        return psycopg2.connect(self.dsn)

    def claim(self, agent):
        with self.conn() as c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(CLAIM_SQL, {"claim": f"claimed by {agent} at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}"})
            return cur.fetchone()

    def reclaim_stale(self, minutes=25):
        with self.conn() as c, c.cursor() as cur:
            cur.execute(RECLAIM_SQL, {"stale": f"{minutes} minutes"})
            n = cur.rowcount
        if n:
            log(f"requeued {n} stale rendering job(s)")
        return n

    def progress(self, job_id, pct, stage, note):
        with self.conn() as c, c.cursor() as cur:
            cur.execute(PROGRESS_SQL, {"note": note[:500], "pct": int(pct), "stage": stage[:120], "id": job_id})

    def deliver(self, job_id, mp4_bytes, gpu_minutes, agent, renderer_name, qa_report):
        artifact_id = f"art-{job_id}-{uuid.uuid4().hex[:8]}"
        with self.conn() as c, c.cursor() as cur:
            cur.execute(DELIVER_ARTIFACT_SQL, {
                "id": artifact_id, "rid": job_id, "bytes": psycopg2.Binary(mp4_bytes),
                "size": len(mp4_bytes),
            })
            cur.execute(DELIVER_ROW_SQL, {
                "gpu": gpu_minutes, "url": f"db-artifact:{artifact_id}", "id": job_id,
                "note": f"rendered by {agent}/{renderer_name} via direct-DB fleet — {qa_report}"[:500],
            })
        return artifact_id

    def fail(self, job_id, agent, reason):
        with self.conn() as c, c.cursor() as cur:
            cur.execute(FAIL_SQL, {"id": job_id, "note": f"{reason} — reported by {agent} at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}"[:1000]})


def main():
    ap = argparse.ArgumentParser(description="DeYoung DB-mode fleet worker")
    ap.add_argument("--dsn", default=os.environ.get("WORKER_DB_DSN", ""))
    ap.add_argument("--renderer", default=os.environ.get("DEYOUNG_RENDERER", "film"))
    ap.add_argument("--prefer", default=os.environ.get("DEYOUNG_PREFER", ""))
    ap.add_argument("--job-budget", type=float, default=float(os.environ.get("DEYOUNG_JOB_BUDGET", "3.0")))
    ap.add_argument("--max-minutes", type=float, default=float(os.environ.get("DEYOUNG_MAX_MINUTES", "480")))
    ap.add_argument("--poll", type=int, default=int(os.environ.get("DEYOUNG_POLL", "45")))
    ap.add_argument("--agent", default=f"kaggle-dbworker-{uuid.uuid4().hex[:6]}")
    ap.add_argument("--exit-idle", action="store_true")
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()

    if not args.dsn:
        sys.exit("db worker: --dsn or WORKER_DB_DSN is required")

    # rewire the shared renderer's progress reporting onto the DB
    db = DB(args.dsn)
    dw.report_progress = lambda job, site, token, pct, stage, note="": db.progress(
        job["id"], pct, stage, note or f"{pct}% — {stage}"
    )
    dw.ARGS = types.SimpleNamespace(prefer=args.prefer)

    started = time.time()
    log(f"up — db fleet mode renderer={args.renderer} prefer={args.prefer or 'default'} agent={args.agent}")

    while True:
        if (time.time() - started) / 60.0 >= args.max_minutes:
            log("time budget reached — stopping cleanly")
            return

        db.reclaim_stale(25)
        job = None
        try:
            job = db.claim(args.agent)
        except Exception as exc:
            log(f"claim failed: {exc.__class__.__name__}: {exc}")
            time.sleep(args.poll)
            continue

        if not job:
            if args.once or args.exit_idle:
                log("queue empty — exiting")
                return
            time.sleep(args.poll)
            continue

        log(f"claimed {job['id']} — {job['seconds']}s {job['resolution']} audio={job['withAudio']} :: {job['prompt'][:70]}…")
        workdir = tempfile.mkdtemp(prefix="deyoung-")
        try:
            site, token = "", ""
            out, gpu_minutes, renderer_name, qa_report = dw.render(
                dict(job), args.renderer, workdir, args.job_budget, site=site, token=token
            )
            size_mb = os.path.getsize(out) / (1024 * 1024)
            with open(out, "rb") as fh:
                mp4 = fh.read()
            artifact = db.deliver(job["id"], mp4, gpu_minutes, args.agent, renderer_name, qa_report)
            log(f"DELIVERED {job['id']} ({size_mb:.1f}MB) -> artifact {artifact} in {gpu_minutes} min")
        except Exception as exc:
            log(f"render failed for {job['id']}: {exc.__class__.__name__}: {str(exc)[:300]}")
            try:
                db.fail(job["id"], args.agent, f"render error: {str(exc)[:400]}")
            except Exception as fail_exc:
                log(f"could not report failure: {fail_exc}")
                time.sleep(args.poll)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

        if args.once:
            return


if __name__ == "__main__":
    main()
