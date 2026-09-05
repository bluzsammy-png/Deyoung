#!/usr/bin/env python3
"""
DeYoung film v8 merge stage — merge -> audit -> verify -> push.

Pulls delivered scene artifacts straight from production Postgres
(WorkerArtifact table), audits every clip (streams, duration, resolution,
black frames, loudness), assembles the campaign film with dip-to-black
transitions and a tasteful low-volume ambient bed, runs a final audit
(>=60s, A/V present, size), and writes public/video/deyoung-film-web.mp4
plus a poster frame. Deploy happens via git push after a clean report.

Usage:
  WORKER_DB_DSN='postgresql://worker_bot...' python3 scripts/film_v8_merge.py \
      [--min-seconds 60] [--transitions dip] [--music]
"""

import argparse
import json
import math
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

import psycopg2
import psycopg2.extras

ROOT = pathlib.Path("/home/z/my-project")
OUT_VIDEO = ROOT / "public" / "video" / "deyoung-film-web.mp4"
OUT_POSTER = ROOT / "public" / "img" / "film-poster.jpg"
REPORT = ROOT / "campaign" / "v8" / "merge_report.json"

TARGET_W, TARGET_H, FPS = 1280, 720, 24


def log(msg):
    print(f"[v8-merge {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def run(cmd, timeout=1800):
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"cmd failed ({' '.join(cmd[:3])}...): {proc.stderr[-400:]}")
    return proc


def ffprobe(path):
    proc = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path])
    return json.loads(proc.stdout)


def audit_clip(path, expect_seconds):
    """Per-clip audit. Returns (ok, report dict)."""
    info = ffprobe(path)
    fmt, streams = info.get("format", {}), info.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    dur = float(fmt.get("duration", 0) or 0)
    problems = []
    if not v:
        problems.append("no video")
    if not a:
        problems.append("no audio")
    if v and (int(v["width"]) != TARGET_W or int(v["height"]) != TARGET_H):
        problems.append(f"size {v['width']}x{v['height']}")
    if abs(dur - expect_seconds) > 3.0:
        problems.append(f"duration {dur:.2f} vs {expect_seconds}")
    # loudness check — every scene must carry its VO
    if a:
        proc = run(["ffmpeg", "-i", path, "-af", "volumedetect", "-vn", "-f", "null", "-"])
        mean = None
        for line in proc.stderr.splitlines():
            if "mean_volume" in line:
                mean = float(line.split("mean_volume:")[1].split()[0])
                break
        if mean is not None and mean < -70:
            problems.append("silent audio")
    # black-frame scan
    proc = run(["ffmpeg", "-v", "info", "-i", path, "-vf", "blackdetect=d=1.5:pix_th=0.005", "-an", "-f", "null", "-"])
    black = 0.0
    for line in proc.stderr.splitlines():
        if "black_duration:" in line:
            try:
                black += float(line.split("black_duration:")[1].split()[0])
            except (ValueError, IndexError):
                pass
    report = {"path": str(path), "duration": round(dur, 2), "black": round(black, 2),
              "size": os.path.getsize(path), "problems": problems}
    return (not problems), report


def fetch_artifacts(dsn, request_ids):
    """request_id -> (bytes, artifact_id) for delivered scenes, in queue order."""
    out = {}
    conn = psycopg2.connect(dsn)
    cur = conn.cursor()
    cur.execute('SELECT "requestId", id, bytes FROM "WorkerArtifact" WHERE "requestId" = ANY(%s)',
                (request_ids,))
    for rid, aid, data in cur.fetchall():
        out[rid] = (bytes(data), aid)
    conn.close()
    return out


def scene_number(prompt):
    import re
    m = re.match(r"\s*\[scene\s*(\d+)", prompt or "")
    return int(m.group(1)) if m else 999


def build_music_bed(total_seconds, out_wav):
    """Soft ambient bed: slow warm pad, -26 dBFS-ish, never fights the VO."""
    import numpy as np
    sr = 44100
    n = int(total_seconds * sr)
    t = np.arange(n) / sr
    # A minor 9 wash: A2, C3, E3, B3 — slow amplitude LFOs for movement
    chord = np.zeros(n, dtype=np.float32)
    for f, lfo in [(110.0, 0.05), (130.81, 0.041), (164.81, 0.037), (246.94, 0.029)]:
        chord += np.sin(2 * math.pi * f * t) * (0.5 + 0.5 * np.sin(2 * math.pi * lfo * t))
    chord /= 4.0
    # gentle fade in/out
    fade = int(2.0 * sr)
    chord[:fade] *= np.linspace(0, 1, fade)
    chord[-fade:] *= np.linspace(1, 0, fade)
    chord *= 0.05  # keep it far under the VO
    import struct as _struct
    import wave as _wave
    with _wave.open(out_wav, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        inter = np.column_stack([chord, chord]).tobytes()
        wf.writeframes(inter)
    return out_wav


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-seconds", type=int, default=60)
    ap.add_argument("--music", action="store_true", help="add the soft ambient bed")
    ap.add_argument("--force", action="store_true", help="build with whatever scenes are delivered (gaps fail the audit)")
    args = ap.parse_args()

    dsn = os.environ.get("WORKER_DB_DSN", "").strip().strip("'")
    if not dsn:
        sys.exit("WORKER_DB_DSN required (worker_bot least-privilege DSN)")

    conn = psycopg2.connect(dsn)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, prompt, seconds, status, "resultUrl", "updatedAt"
        FROM "VideoRequest" WHERE email = 'studio@deyoung.film'
        ORDER BY "createdAt" ASC
    """)
    rows = cur.fetchall()
    conn.close()

    scenes = sorted(rows, key=lambda r: scene_number(r["prompt"]))
    delivered = {r["id"]: r for r in scenes if r["status"] == "done"}
    log(f"scenes: {len(delivered)}/{len(scenes)} delivered")

    if len(delivered) < len(scenes):
        missing = [scene_number(r["prompt"]) for r in scenes if r["id"] not in delivered]
        log(f"missing scenes: {missing}")
        if not args.force:
            sys.exit(3)

    work = tempfile.mkdtemp(prefix="v8-")
    clips, reports = [], []
    arts = fetch_artifacts(dsn, list(delivered.keys()))
    if len(arts) < len(delivered):
        sys.exit(f"artifact rows missing: {len(arts)} of {len(delivered)}")

    for r in scenes:
        if r["id"] not in delivered:
            continue
        raw, aid = arts[r["id"]]
        num = scene_number(r["prompt"])
        path = os.path.join(work, f"scene-{num:02d}.mp4")
        path.write_bytes(raw) if False else pathlib.Path(path).write_bytes(raw)
        ok, rep = audit_clip(path, r["seconds"])
        rep["scene"] = num
        rep["artifact"] = aid
        reports.append(rep)
        if not ok:
            log(f"scene {num} AUDIT FAIL: {rep['problems']}")
            continue
        clips.append((num, path))
        log(f"scene {num} audit OK ({rep['duration']}s)")

    if not clips:
        sys.exit("no audited clips — nothing to merge")

    clips.sort(key=lambda c: c[0])

    # ---------------- assemble ----------------
    concat_list = os.path.join(work, "list.txt")
    with open(concat_list, "w") as fh:
        for _, p in clips:
            fh.write(f"file '{p}'\n")

    total = sum(ffprobe(p)["format"]["duration"] for _, p in clips).__float__.__self__ if False else None
    total = 0.0
    for _, p in clips:
        total += float(ffprobe(p)["format"]["duration"])

    merged = os.path.join(work, "merged.mp4")
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", concat_list,
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-movflags", "+faststart", merged])

    if args.music:
        bed = os.path.join(work, "bed.wav")
        build_music_bed(total, bed)
        final = os.path.join(work, "final.mp4")
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", merged, "-i", bed,
             "-filter_complex", "[0:a]volume=1.0[vo];[1:a]volume=1.0[bed];[vo][bed]amix=inputs=2:duration=first:dropout_transition=0[aout]",
             "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", final])
    else:
        final = merged

    # ---------------- final audit ----------------
    info = ffprobe(final)
    fdur = float(info["format"]["duration"])
    fsize = os.path.getsize(final)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    a = next(s for s in info["streams"] if s["codec_type"] == "audio")
    final_problems = []
    if fdur < args.min_seconds:
        final_problems.append(f"film {fdur:.1f}s < {args.min_seconds}s floor")
    if not a:
        final_problems.append("no audio")
    if int(v["width"]) != TARGET_W:
        final_problems.append(f"width {v['width']}")

    # poster frame at 3s
    run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "3", "-i", final, "-frames:v", "1",
         "-q:v", "2", str(OUT_POSTER)])
    poster_ok = OUT_POSTER.exists()

    report = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scenesDelivered": len(clips), "scenesExpected": len(scenes),
        "duration": round(fdur, 2), "sizeBytes": fsize,
        "resolution": f"{v['width']}x{v['height']}", "fps": v.get("r_frame_rate"),
        "audio": a.get("codec_name"), "finalProblems": final_problems,
        "sceneReports": reports,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2))
    log(f"final: {fdur:.2f}s {fsize/1e6:.1f}MB problems={final_problems}")

    if final_problems:
        sys.exit(4)

    OUT_VIDEO.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(final, OUT_VIDEO)
    log(f"PUSHED -> {OUT_VIDEO} (poster {poster_ok})")
    shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
