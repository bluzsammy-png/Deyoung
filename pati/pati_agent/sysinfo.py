"""Hardware / resource inspection for heartbeats and sys.report jobs."""
from __future__ import annotations

import subprocess
import shutil


def _gpu_report() -> list[dict]:
    """Best-effort NVIDIA detection via nvidia-smi (free, no SDK needed)."""
    if shutil.which("nvidia-smi") is None:
        return []
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5)
        gpus = []
        for line in out.stdout.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) == 4:
                gpus.append({"name": parts[0], "memory_total_mb": parts[1],
                             "memory_used_mb": parts[2], "utilization_pct": parts[3]})
        return gpus
    except Exception:
        return []


def resource_report(roots: list[str] | None = None) -> dict:
    import psutil
    vm = psutil.virtual_memory()
    report = {
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "cpu_count": psutil.cpu_count(logical=True),
        "ram_total_mb": round(vm.total / 1e6, 1),
        "ram_used_mb": round(vm.used / 1e6, 1),
        "ram_percent": vm.percent,
        "gpus": _gpu_report(),
        "has_gpu": bool(_gpu_report()),
        "disks": [],
    }
    for root in (roots or [])[:5]:
        try:
            du = shutil.disk_usage(root)
            report["disks"].append({"root": root, "total_gb": round(du.total / 1e9, 1),
                                    "free_gb": round(du.free / 1e9, 1)})
        except OSError:
            continue
    return report


def machine_profile() -> dict:
    import platform
    import socket
    return {
        "hostname": socket.gethostname(),
        "system": platform.system(),
        "release": platform.release(),
        "python": platform.python_version(),
    }
