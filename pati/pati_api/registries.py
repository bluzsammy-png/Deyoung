"""Capability-first registries: capabilities, models, tools.

Everything external sits behind metadata here. FREE_ONLY is enforced:
every model/tool entry must carry cost == 0 and a free_status of
FREE_FOREVER / FREE_WITH_LIMITS / OPEN_SOURCE_SELF_HOSTED.
"""
from __future__ import annotations

import json
import time
from typing import Optional

from . import config, db

# ---------------------------------------------------------------------------
# WORKER TYPES
# ---------------------------------------------------------------------------
WORKER_TYPES = [
    "LOCAL_WORKER", "KAGGLE_WORKER", "CONTAINER_WORKER", "BATCH_WORKER",
    "REMOTE_FREE_WORKER", "OPTIONAL_CLOUD_WORKER", "BROWSER_WORKER",
    "CPU_WORKER", "GPU_WORKER", "VIDEO_WORKER", "AUDIO_WORKER",
    "IMAGE_WORKER", "CODING_WORKER", "RESEARCH_WORKER", "DEPLOYMENT_WORKER",
]

# ---------------------------------------------------------------------------
# CAPABILITY REGISTRY  (id, category, description, risky, min_autonomy_level)
# Autonomy levels: 0 read-only .. 6 destructive (see docs/AUTONOMY.md)
# ---------------------------------------------------------------------------


def _worker_types_for(cid: str) -> list[str]:
    mapping = {
        "local_fs": ["LOCAL_WORKER"],
        "text": ["KAGGLE_WORKER", "CPU_WORKER", "GPU_WORKER", "REMOTE_FREE_WORKER"],
        "coding": ["CODING_WORKER", "KAGGLE_WORKER", "CONTAINER_WORKER", "LOCAL_WORKER"],
        "research": ["RESEARCH_WORKER", "KAGGLE_WORKER", "LOCAL_WORKER"],
        "vision": ["GPU_WORKER", "KAGGLE_WORKER"],
        "image": ["IMAGE_WORKER", "GPU_WORKER", "KAGGLE_WORKER"],
        "video": ["VIDEO_WORKER", "GPU_WORKER", "KAGGLE_WORKER"],
        "audio": ["AUDIO_WORKER", "GPU_WORKER", "KAGGLE_WORKER"],
        "automation": ["LOCAL_WORKER", "BROWSER_WORKER", "CODING_WORKER"],
        "app": ["CODING_WORKER", "CONTAINER_WORKER", "KAGGLE_WORKER"],
        "infrastructure": ["CONTAINER_WORKER", "GPU_WORKER", "BATCH_WORKER", "KAGGLE_WORKER", "LOCAL_WORKER"],
    }
    cat = _CATEGORY_HINT.get(cid)
    if cid.startswith("filesystem") or cid in ("artifact_save_local", "report_generation",
                                               "run_scripts", "run_commands", "run_local_models",
                                               "system_inspection"):
        return ["LOCAL_WORKER"]
    if cat in mapping:
        return mapping[cat]
    return ["LOCAL_WORKER", "KAGGLE_WORKER", "GPU_WORKER"]


_CATEGORY_HINT = {c[0]: c[1] for c in [
    ("text_generation", "text"), ("reasoning", "text"), ("summarization", "text"),
    ("translation", "text"), ("structured_output", "text"), ("classification", "text"),
    ("extraction", "text"), ("rewriting", "text"), ("question_answering", "text"),
    ("coding", "coding"), ("code_generation", "coding"), ("code_review", "coding"),
    ("debugging", "coding"), ("refactoring", "coding"), ("repository_analysis", "coding"),
    ("coding_agent", "coding"), ("test_generation", "coding"),
    ("documentation_generation", "coding"), ("architecture_generation", "coding"),
    ("web_research", "research"), ("document_research", "research"),
    ("source_comparison", "research"), ("fact_checking", "research"),
    ("literature_research", "research"), ("market_research", "research"),
    ("technical_research", "research"), ("research_synthesis", "research"),
    ("vision", "vision"), ("image_understanding", "vision"), ("OCR", "vision"),
    ("document_vision", "vision"), ("image_captioning", "vision"),
    ("visual_question_answering", "vision"),
    ("image_generation", "image"), ("image_editing", "image"), ("image_to_image", "image"),
    ("image_upscaling", "image"), ("background_removal", "image"),
    ("character_generation", "image"), ("character_consistency", "image"),
    ("text_to_video", "video"), ("image_to_video", "video"), ("video_to_video", "video"),
    ("video_upscaling", "video"), ("frame_interpolation", "video"),
    ("video_editing", "video"), ("storyboard_generation", "video"),
    ("scene_generation", "video"), ("character_consistency_video", "video"),
    ("text_to_speech", "audio"), ("speech_to_text", "audio"), ("voice_conversion", "audio"),
    ("voice_generation", "audio"), ("lip_sync", "audio"), ("music_generation", "audio"),
    ("audio_processing", "audio"),
    ("browser_automation", "automation"), ("web_scraping", "automation"),
    ("filesystem_operations", "automation"), ("git_operations", "automation"),
    ("github_operations", "automation"), ("API_operations", "automation"),
    ("scheduled_tasks", "automation"),
    ("app_generation", "app"), ("frontend_generation", "app"), ("backend_generation", "app"),
    ("database_generation", "app"), ("testing", "app"), ("browser_testing", "app"),
    ("deployment", "app"), ("CI_CD", "app"), ("security_scanning", "app"),
    ("container_execution", "infrastructure"), ("GPU_execution", "infrastructure"),
    ("batch_execution", "infrastructure"), ("remote_execution", "infrastructure"),
    ("artifact_storage", "infrastructure"), ("benchmarking", "infrastructure"),
    ("model_evaluation", "infrastructure"), ("tool_evaluation", "infrastructure"),
]}

_C = [
    # TEXT
    ("text_generation", "text", "Generate natural-language text from prompts", False, 1),
    ("reasoning", "text", "Multi-step reasoning and analysis", False, 1),
    ("summarization", "text", "Summarize documents or corpora", False, 1),
    ("translation", "text", "Translate between languages", False, 1),
    ("structured_output", "text", "Produce schema-valid JSON/structured output", False, 1),
    ("classification", "text", "Classify inputs into categories", False, 1),
    ("extraction", "text", "Extract entities/fields from text", False, 1),
    ("rewriting", "text", "Rewrite or restyle text", False, 1),
    ("question_answering", "text", "Answer questions over context", False, 1),
    # CODING
    ("coding", "coding", "Write and modify code", False, 2),
    ("code_generation", "coding", "Generate code from specification", False, 2),
    ("code_review", "coding", "Review code for issues", False, 1),
    ("debugging", "coding", "Diagnose and fix code defects", False, 2),
    ("refactoring", "coding", "Restructure code safely", False, 2),
    ("repository_analysis", "coding", "Analyze repository structure", False, 1),
    ("coding_agent", "coding", "Autonomous multi-step coding agent", True, 3),
    ("test_generation", "coding", "Generate tests for code", False, 2),
    ("documentation_generation", "coding", "Generate documentation", False, 2),
    ("architecture_generation", "coding", "Design system architecture", False, 1),
    # RESEARCH
    ("web_research", "research", "Search and read web sources", False, 4),
    ("document_research", "research", "Research over provided documents", False, 1),
    ("source_comparison", "research", "Compare and cross-check sources", False, 1),
    ("fact_checking", "research", "Verify claims against sources", False, 1),
    ("literature_research", "research", "Academic literature research", False, 4),
    ("market_research", "research", "Market and competitor research", False, 4),
    ("technical_research", "research", "Technical due diligence", False, 4),
    ("research_synthesis", "research", "Synthesize research into outputs", False, 1),
    # VISION
    ("vision", "vision", "Understand images", False, 1),
    ("image_understanding", "vision", "Describe and analyze images", False, 1),
    ("OCR", "vision", "Extract text from images", False, 1),
    ("document_vision", "vision", "Understand document images/PDFs", False, 1),
    ("image_captioning", "vision", "Caption images", False, 1),
    ("visual_question_answering", "vision", "Answer questions about images", False, 1),
    # IMAGE
    ("image_generation", "image", "Generate images from text", False, 2),
    ("image_editing", "image", "Edit images by instruction", False, 2),
    ("image_to_image", "image", "Transform images", False, 2),
    ("image_upscaling", "image", "Upscale image resolution", False, 2),
    ("background_removal", "image", "Remove image backgrounds", False, 2),
    ("character_generation", "image", "Generate consistent characters", False, 2),
    ("character_consistency", "image", "Keep characters consistent across assets", False, 2),
    # VIDEO
    ("text_to_video", "video", "Generate video from text", False, 2),
    ("image_to_video", "video", "Animate images into video", False, 2),
    ("video_to_video", "video", "Restyle or transform video", False, 2),
    ("video_upscaling", "video", "Upscale video resolution", False, 2),
    ("frame_interpolation", "video", "Interpolate frames for smoothness", False, 2),
    ("video_editing", "video", "Cut, join and edit video", False, 2),
    ("storyboard_generation", "video", "Generate storyboards from scripts", False, 1),
    ("scene_generation", "video", "Generate individual scenes", False, 2),
    ("character_consistency_video", "video", "Consistent characters across scenes", False, 2),
    # AUDIO
    ("text_to_speech", "audio", "Synthesize speech from text", False, 2),
    ("speech_to_text", "audio", "Transcribe audio", False, 2),
    ("voice_conversion", "audio", "Convert voice identity", False, 2),
    ("voice_generation", "audio", "Generate synthetic voices", False, 2),
    ("lip_sync", "audio", "Lip-sync video to audio", False, 2),
    ("music_generation", "audio", "Generate music", False, 2),
    ("audio_processing", "audio", "Mix, normalize, process audio", False, 2),
    # AUTOMATION
    ("browser_automation", "automation", "Drive a browser safely", True, 4),
    ("web_scraping", "automation", "Scrape permitted web content", False, 4),
    ("filesystem_operations", "automation", "Authorized local file operations", True, 1),
    ("git_operations", "automation", "Run git operations", True, 2),
    ("github_operations", "automation", "Interact with GitHub APIs", False, 4),
    ("API_operations", "automation", "Call approved external APIs", False, 4),
    ("scheduled_tasks", "automation", "Schedule recurring tasks", False, 2),
    # APP BUILDING
    ("app_generation", "app", "Generate full applications", True, 3),
    ("frontend_generation", "app", "Generate frontend code", False, 3),
    ("backend_generation", "app", "Generate backend code", False, 3),
    ("database_generation", "app", "Design and generate databases", False, 3),
    ("testing", "app", "Run test suites", False, 3),
    ("browser_testing", "app", "Automated browser testing", True, 3),
    ("deployment", "app", "Deploy applications", True, 5),
    ("CI_CD", "app", "Build CI/CD pipelines", True, 5),
    ("security_scanning", "app", "Scan code for vulnerabilities", False, 2),
    # INFRASTRUCTURE (incl. granular filesystem ops for the Local Agent)
    ("container_execution", "infrastructure", "Run containers", True, 3),
    ("GPU_execution", "infrastructure", "Run GPU workloads", True, 3),
    ("batch_execution", "infrastructure", "Run batch jobs", True, 3),
    ("remote_execution", "infrastructure", "Execute on remote workers", True, 3),
    ("artifact_storage", "infrastructure", "Store and retrieve artifacts", False, 1),
    ("benchmarking", "infrastructure", "Benchmark models/tools", False, 2),
    ("model_evaluation", "infrastructure", "Evaluate model quality", False, 2),
    ("tool_evaluation", "infrastructure", "Evaluate tool quality", False, 2),
    # LOCAL FILESYSTEM (granular, Local Agent enforced)
    ("filesystem_read", "local_fs", "Read authorized files", False, 1),
    ("filesystem_create", "local_fs", "Create files/dirs in authorized roots", True, 1),
    ("filesystem_modify", "local_fs", "Modify authorized files", True, 1),
    ("filesystem_copy", "local_fs", "Copy files in authorized roots", True, 1),
    ("filesystem_move", "local_fs", "Move files in authorized roots", True, 1),
    ("filesystem_delete", "local_fs", "Delete files (dangerous, default off)", True, 6),
    ("filesystem_list", "local_fs", "List authorized directories", False, 1),
    ("filesystem_organize", "local_fs", "Organize files into project folders", True, 1),
    ("artifact_save_local", "local_fs", "Save artifacts to authorized local folders", True, 1),
    ("report_generation", "local_fs", "Generate report files locally", False, 1),
    ("run_scripts", "local_fs", "Run approved local scripts", True, 3),
    ("run_commands", "local_fs", "Run allowlisted local commands", True, 3),
    ("run_local_models", "local_fs", "Run lightweight local models", True, 3),
    ("system_inspection", "local_fs", "Report hardware/resource status", False, 1),
]

CAPABILITIES: dict[str, dict] = {}
for cid, cat, desc, risky, lvl in _C:
    CAPABILITIES[cid] = {
        "capability_id": cid, "category": cat, "description": desc,
        "risky": risky, "min_autonomy_level": lvl,
        "worker_types": _worker_types_for(cid),
    }


# ---------------------------------------------------------------------------
# MODEL REGISTRY (all $0; Kaggle-hosted open-weights are FREE_WITH_LIMITS)
# ---------------------------------------------------------------------------
def _model(mid, name, org, provider, modality, caps, license, vram, ram, status,
           notes, kaggle_model=None, quant=None, ctx=8192, verified="2026-09-02"):
    return {
        "model_id": mid, "name": name, "organization": org, "provider": provider,
        "version": "1", "modality": modality, "capabilities": caps,
        "license": license,
        "license_url": "https://huggingface.co/" + (kaggle_model or name.lower().replace(" ", "-")) ,
        "source_url": "https://www.kaggle.com/models" if provider == "kaggle-hosted" else "https://ollama.com/library",
        "repository_url": "https://www.kaggle.com/models" if provider == "kaggle-hosted" else "https://ollama.com",
        "model_url": f"https://www.kaggle.com/models/{kaggle_model}" if kaggle_model else None,
        "hardware_requirements": ("GPU (Kaggle free T4/P100)" if provider == "kaggle-hosted" else "CPU 8GB RAM"),
        "RAM_requirement": ram, "VRAM_requirement": vram,
        "quantization_options": quant or ["fp16", "int8", "int4"],
        "context_length": ctx, "languages": ["multi"],
        "input_types": ["text"] if modality == "text" else [modality],
        "output_types": ["text"] if modality == "text" else [modality],
        "latency_estimate": "minutes (kernel queue + run)" if provider == "kaggle-hosted" else "seconds (local)",
        "quality_score": 0.75, "speed_score": 0.5,
        "cost": 0, "free_status": "FREE_WITH_LIMITS" if provider == "kaggle-hosted" else "OPEN_SOURCE_SELF_HOSTED",
        "availability": status,
        "worker_requirements": ["KAGGLE_WORKER"] if provider == "kaggle-hosted" else ["LOCAL_WORKER", "CPU_WORKER"],
        "startup_time": "1-5 min", "cold_start_time": "2-10 min",
        "max_context": ctx,
        "tool_calling_support": modality == "text", "structured_output_support": True,
        "vision_support": modality in ("vision", "image"), "reasoning_support": modality == "text",
        "commercial_use": "per upstream license",
        "license_restrictions": "see license_url",
        "known_limitations": notes,
        "benchmark_results": [], "last_verified": verified, "status": status,
        "kaggle_model": kaggle_model,
    }


MODELS: list[dict] = [
    _model("pati-sim-text-v1", "PATI Simulated Text Engine", "PATI", "builtin", "text",
           ["text_generation", "summarization", "storyboard_generation"], "MIT", "0", "0.1GB",
           "active", "Deterministic simulated generator for testing/demo; clearly labeled simulated."),
    _model("pati-sim-image-v1", "PATI Simulated Image Engine", "PATI", "builtin", "image",
           ["image_generation"], "MIT", "0", "0.1GB", "active",
           "Deterministic placeholder image generator for testing/demo (simulated:true)."),
    _model("pati-sim-video-v1", "PATI Simulated Video Engine", "PATI", "builtin", "video",
           ["text_to_video", "image_to_video", "video_editing"], "MIT", "0", "0.1GB", "active",
           "Deterministic placeholder video generator for testing/demo (simulated:true)."),
    _model("pati-sim-audio-v1", "PATI Simulated Audio Engine", "PATI", "builtin", "audio",
           ["text_to_speech", "music_generation"], "MIT", "0", "0.1GB", "active",
           "Deterministic placeholder audio generator for testing/demo (simulated:true)."),
    _model("qwen2.5-7b-instruct", "Qwen2.5 7B Instruct", "Alibaba Qwen", "kaggle-hosted", "text",
           ["text_generation", "reasoning", "summarization", "structured_output", "coding",
            "code_generation", "rewriting", "question_answering", "translation", "extraction",
            "classification", "research_synthesis"],
           "Apache-2.0", "16GB", "8GB", "available_when_kaggle_configured",
           "Strong general instruction model; runs as Kaggle kernel with Kaggle-hosted weights (no download needed).",
           kaggle_model="qwenlm/qwen2.5/transformers/7b-instruct"),
    _model("llama-3.2-3b-instruct", "Llama 3.2 3B Instruct", "Meta", "kaggle-hosted", "text",
           ["text_generation", "summarization", "rewriting", "question_answering"],
           "Llama 3.2 Community", "8GB", "8GB", "available_when_kaggle_configured",
           "Small fast instruct model on Kaggle GPU.",
           kaggle_model="meta-llama/llama-3.2/transformers/3b-instruct"),
    _model("gemma-2-2b-it", "Gemma 2 2B IT", "Google", "kaggle-hosted", "text",
           ["text_generation", "summarization", "classification", "extraction"],
           "Gemma", "8GB", "8GB", "available_when_kaggle_configured",
           "Compact Gemma instruct model on Kaggle GPU.",
           kaggle_model="google/gemma-2/transformers/2b-it"),
    _model("sdxl-1.0", "Stable Diffusion XL 1.0", "Stability AI", "kaggle-hosted", "image",
           ["image_generation", "image_to_image", "character_generation"],
           "CreativeML Open RAIL++-M", "16GB", "8GB", "available_when_kaggle_configured",
           "High-quality image generation as Kaggle GPU kernel; outputs pulled back as artifacts.",
           kaggle_model="stabilityai/stable-diffusion-xl/1.0"),
    _model("sd-1.5", "Stable Diffusion 1.5", "CompVis/Runway", "kaggle-hosted", "image",
           ["image_generation", "image_to_image", "background_removal"],
           "CreativeML Open RAIL-M", "8GB", "8GB", "available_when_kaggle_configured",
           "Faster/lighter image generation kernel.",
           kaggle_model="stabilityai/stable-diffusion/1.5"),
    _model("whisper-large-v3", "Whisper Large v3", "OpenAI (open weights)", "kaggle-hosted", "audio",
           ["speech_to_text", "OCR"], "Apache-2.0", "16GB", "8GB", "available_when_kaggle_configured",
           "Speech recognition kernel; audio uploaded as job input.",
           kaggle_model="openai/whisper/transformers/large-v3"),
    _model("xtts-v2", "Coqui XTTS v2", "Coqui", "kaggle-hosted", "audio",
           ["text_to_speech", "voice_generation"], "Coqui Public Model (non-commercial)",
           "8GB", "8GB", "available_when_kaggle_configured",
           "Multilingual TTS; NON-COMMERCIAL license - flagged; use Piper for commercial.",
           kaggle_model="coqui/xtts/2"),
    _model("piper-tts", "Piper TTS", "Rhasspy", "kaggle-hosted", "audio",
           ["text_to_speech", "voice_generation"], "MIT", "2GB", "2GB", "available_when_kaggle_configured",
           "Fast MIT-licensed neural TTS, commercial-use friendly.",
           kaggle_model=None),
    _model("musicgen-small", "MusicGen Small", "Meta", "kaggle-hosted", "audio",
           ["music_generation"], "CC-BY-NC 4.0 (weights)", "16GB", "8GB",
           "available_when_kaggle_configured", "Music generation; NC license - personal use.",
           kaggle_model="facebook/musicgen/small"),
]

# ---------------------------------------------------------------------------
# TOOL REGISTRY
# ---------------------------------------------------------------------------
def _tool(tid, name, desc, cat, caps, worker_type, status="active", sandbox=False,
          fallback=None, op=None, license="MIT", network="none"):
    return {
        "tool_id": tid, "name": name, "description": desc, "category": cat,
        "capabilities": caps, "version": "1.0.0", "source": "pati-builtin",
        "repository": "https://github.com/pati/pati", "documentation": "docs/TOOL_REGISTRY.md",
        "license": license, "install_method": "builtin", "runtime": "python",
        "dependencies": [], "hardware_requirements": "none",
        "network_requirements": network, "input_schema": {"type": "object"},
        "output_schema": {"type": "object"}, "health_check": "builtin",
        "benchmark_command": None, "security_profile": "policy-enforced",
        "sandbox_required": sandbox, "worker_type": worker_type,
        "startup_command": None, "shutdown_command": None,
        "status": status, "last_verified": "2026-09-02",
        "commercial_use": True, "free_status": "FREE_FOREVER",
        "fallback_tools": fallback or [], "adapter": "builtin", "op": op or tid,
    }


TOOLS: list[dict] = [
    _tool("fs.list", "List Directory", "List an authorized directory", "local_fs",
          ["filesystem_list"], "LOCAL_WORKER", op="fs.list"),
    _tool("fs.read", "Read File", "Read an authorized file", "local_fs",
          ["filesystem_read"], "LOCAL_WORKER", op="fs.read"),
    _tool("fs.mkdir", "Create Folder", "Create a folder in authorized roots", "local_fs",
          ["filesystem_create"], "LOCAL_WORKER", op="fs.mkdir"),
    _tool("fs.create_file", "Create File", "Create a file with content", "local_fs",
          ["filesystem_create"], "LOCAL_WORKER", op="fs.create_file"),
    _tool("fs.move", "Move File", "Move/rename files within authorized roots", "local_fs",
          ["filesystem_move"], "LOCAL_WORKER", op="fs.move"),
    _tool("fs.copy", "Copy File", "Copy files within authorized roots", "local_fs",
          ["filesystem_copy"], "LOCAL_WORKER", op="fs.copy"),
    _tool("fs.delete", "Delete File", "Delete files (requires DELETE_FILES permission)",
          "local_fs", ["filesystem_delete"], "LOCAL_WORKER", sandbox=True, op="fs.delete"),
    _tool("fs.organize", "Organize Folder", "Create project folder and organize media by type",
          "local_fs", ["filesystem_organize", "filesystem_create", "filesystem_move"],
          "LOCAL_WORKER", op="fs.organize"),
    _tool("artifact.save", "Save Artifact", "Download a PATI artifact into an authorized local folder",
          "local_fs", ["artifact_save_local"], "LOCAL_WORKER", op="artifact.save"),
    _tool("report.markdown", "Markdown Report", "Write a markdown report file locally", "local_fs",
          ["report_generation"], "LOCAL_WORKER", op="report.markdown"),
    _tool("sys.report", "System Report", "Report CPU/RAM/disk/GPU status", "local_fs",
          ["system_inspection"], "LOCAL_WORKER", op="sys.report"),
    _tool("script.run", "Run Script", "Run an approved script inside resource limits", "local_fs",
          ["run_scripts"], "LOCAL_WORKER", sandbox=True, op="script.run"),
    _tool("command.run", "Run Command", "Run an allowlisted command inside limits", "local_fs",
          ["run_commands"], "LOCAL_WORKER", sandbox=True, op="command.run"),
    _tool("research.local_search", "Local Corpus Search", "Search authorized local files for research",
          "research", ["document_research"], "LOCAL_WORKER", op="research.local_search"),
    _tool("sim.text_generate", "Simulated Text", "Deterministic simulated text generation",
          "text", ["text_generation"], "CPU_WORKER", op="sim.text_generate"),
    _tool("sim.image_generate", "Simulated Image", "Deterministic simulated image generation",
          "image", ["image_generation"], "GPU_WORKER", op="sim.image_generate"),
    _tool("sim.video_render", "Simulated Video", "Deterministic simulated video render",
          "video", ["text_to_video", "video_editing"], "GPU_WORKER", op="sim.video_render"),
    _tool("sim.tts", "Simulated TTS", "Deterministic simulated speech synthesis",
          "audio", ["text_to_speech"], "GPU_WORKER", op="sim.tts"),
    _tool("sim.music", "Simulated Music", "Deterministic simulated music generation",
          "audio", ["music_generation"], "GPU_WORKER", op="sim.music"),
    _tool("kaggle.kernel_run", "Kaggle Kernel Run", "Push and run a Kaggle kernel job on free GPU",
          "infrastructure", ["GPU_execution", "text_generation", "image_generation",
                             "text_to_video", "text_to_speech"],
          "KAGGLE_WORKER", status="available_when_configured", network="internet",
          license="Apache-2.0 (client)", op="kaggle.kernel_run"),
    _tool("container.run", "Container Run", "Run job in a local container",
          "infrastructure", ["container_execution"], "CONTAINER_WORKER",
          status="available_when_docker_present", sandbox=True, op="container.run"),
    _tool("git.commit", "Git Operations", "Commit/push via git connector",
          "automation", ["git_operations"], "LOCAL_WORKER",
          status="requires_connector", op="git.commit"),
    _tool("drive.read", "Drive Read", "Read files from Google Drive via connector",
          "automation", ["web_scraping"], "LOCAL_WORKER",
          status="requires_connector", network="internet", op="drive.read"),
    _tool("web.scrape", "Web Scrape", "Scrape permitted pages (future: trafilatura)",
          "research", ["web_research"], "RESEARCH_WORKER", status="planned",
          network="internet", op="web.scrape"),
]


def merged_capabilities(tenant_id: str) -> list[dict]:
    rows = db.query("SELECT * FROM registered_capabilities")
    out = list(CAPABILITIES.values())
    for r in rows:
        out.append({
            "capability_id": r["id"], "category": r["category"], "description": r["description"],
            "risky": bool(r["risky"]), "min_autonomy_level": r["min_level"], "worker_types": [],
        })
    return out


def merged_models(tenant_id: str) -> list[dict]:
    rows = db.query("SELECT doc FROM registered_models")
    out = list(MODELS)
    for r in rows:
        out.append(json.loads(r["doc"]))
    return out


def merged_tools(tenant_id: str) -> list[dict]:
    rows = db.query("SELECT doc FROM registered_tools")
    out = [dict(t) for t in TOOLS]
    installed = {r["tool_id"]: r["status"] for r in db.query("SELECT * FROM installed_tools")}
    for t in out:
        if t["tool_id"] in installed:
            t["status"] = installed[t["tool_id"]]
    for r in rows:
        out.append(json.loads(r["doc"]))
    return out


def tools_by_capability(tenant_id: str, capability: str) -> list[dict]:
    return [t for t in merged_tools(tenant_id) if capability in t["capabilities"]]


def models_by_capability(tenant_id: str, capability: str) -> list[dict]:
    return [m for m in merged_models(tenant_id) if capability in m["capabilities"]]


def enforce_free_only(entries: list[dict]) -> list[dict]:
    """Hard FREE_ONLY enforcement: reject any entry with cost > 0 or paid status."""
    ok = []
    for e in entries:
        if e.get("cost", 0) != 0:
            db.execute("INSERT INTO audit(ts, actor, action, resource, detail) VALUES (?,?,?,?,?)",
                       (time.time(), "policy", "reject_paid_entry", e.get("model_id") or e.get("tool_id"), "cost>0 blocked"))
            continue
        if e.get("free_status") in ("PAID", "FREE_TRIAL", "UNKNOWN"):
            db.execute("INSERT INTO audit(ts, actor, action, resource, detail) VALUES (?,?,?,?,?)",
                       (time.time(), "policy", "reject_paid_entry", e.get("model_id") or e.get("tool_id"),
                        f"free_status={e.get('free_status')} blocked"))
            continue
        ok.append(e)
    return ok
