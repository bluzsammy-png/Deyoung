"""Planner: turns a high-level objective into a stage graph (execution plan).

Rule-based and capability-first. Every stage declares:
  capability  - what is needed
  tool        - preferred tool id (informational; router picks worker)
  op          - op name the worker will execute
  params      - op parameters
  depends_on  - stage names that must finish first
  group       - parallel group; stages sharing a group can run concurrently

The planner is provider-independent: it never names a paid service.
"""
from __future__ import annotations

import re
from typing import Optional


def classify_objective(objective: str, explicit: Optional[str] = None) -> str:
    if explicit and explicit != "auto":
        return explicit
    t = objective.lower()
    checks = [
        ("filesystem_organize", ["organize", "folder called", "folder named", "move my files",
                                 "tidy", "collect my", "project folder"]),
        ("video_workflow", ["video", "animated story", "youtube", "reel", "short film",
                            "text to video", "image-to-video"]),
        ("image_generation", ["image", "picture", "photo of", "illustration", "poster",
                              "generate art", "wallpaper"]),
        ("voice_generation", ["voice", "text to speech", "tts", "narration", "speak"]),
        ("speech_to_text", ["transcribe", "speech to text", "subtitles", "captions"]),
        ("music_generation", ["music", "soundtrack", "background track", "sfx"]),
        ("research", ["research", "find papers", "investigate", "market research",
                      "summarize the research", "literature"]),
        ("document", ["report", "document", "write up", "pdf report", "brief"]),
        ("coding", ["code", "app", "script that", "program", "bug", "refactor", "test"]),
        ("text_generation", ["write", "story", "script", "summarize", "draft", "blog",
                             "email", "translate"]),
    ]
    for name, kws in checks:
        if any(k in t for k in kws):
            return name
    return "generic"


def _stage(seq, name, capability, op, params=None, depends_on=None, group=None, tool=None):
    return {
        "seq": seq, "name": name, "capability": capability, "op": op,
        "params": params or {}, "depends_on": depends_on or [],
        "group": group, "tool": tool,
    }


def _extract_folder(objective: str, params: dict) -> Optional[str]:
    if params.get("target_folder"):
        return str(params["target_folder"])
    m = re.search(
        r'folder (?:called|named)\s+["\u201c]?(.+?)["\u201d]?'
        r'(?:\s+in\s+|\s+and\s+|\s+then\s+|,|\.|$)',
        objective, re.I)
    if m:
        return m.group(1).strip()
    return None


def _extract_scene_count(objective: str, params: dict) -> int:
    if params.get("scenes"):
        return int(params["scenes"])
    m = re.search(r"(\d+)\s*(?:second|sec)", objective.lower())
    seconds = int(m.group(1)) if m else 60
    return max(1, min(6, seconds // 20))


def plan_task(task_type: str, objective: str, params: dict, constraints: dict) -> dict:
    """Return {title, capability, stages:[...]} for the objective."""
    params = dict(params or {})
    if task_type == "filesystem_organize":
        folder = _extract_folder(objective, params) or "New Project"
        root = params.get("root")
        return {
            "title": f"Organize: {folder}",
            "capability": "filesystem_organize",
            "stages": [_stage(1, "organize_workspace", "filesystem_organize", "fs.organize",
                              {"objective": objective, "target_folder": folder, "root": root,
                               "workspace": params.get("workspace")})],
        }

    if task_type == "video_workflow":
        n = _extract_scene_count(objective, params)
        stages, seq = [], 1
        stages.append(_stage(seq, "story", "text_generation", "generate_text",
                             {"prompt": f"Create a story outline for: {objective}"}, tool="sim.text_generate")); seq += 1
        stages.append(_stage(seq, "script", "text_generation", "generate_text",
                             {"prompt": "Expand the story into a scene-by-scene script"},
                             depends_on=["story"], tool="sim.text_generate")); seq += 1
        stages.append(_stage(seq, "character_bible", "text_generation", "generate_text",
                             {"prompt": "Create a character bible for consistent characters"},
                             depends_on=["script"], tool="sim.text_generate")); seq += 1
        stages.append(_stage(seq, "storyboard", "storyboard_generation", "generate_text",
                             {"prompt": "Break the script into storyboard shots"},
                             depends_on=["character_bible"], tool="sim.text_generate")); seq += 1
        image_ids, video_ids = [], []
        for i in range(1, n + 1):
            sid = f"scene_image_{i}"
            stages.append(_stage(seq, sid, "image_generation", "generate_image",
                                 {"scene": i, "prompt": f"Scene {i} keyframe"},
                                 depends_on=["storyboard"], group="scenes",
                                 tool="sim.image_generate"))
            image_ids.append(sid); seq += 1
        for i in range(1, n + 1):
            sid = f"scene_video_{i}"
            stages.append(_stage(seq, sid, "image_to_video", "generate_video",
                                 {"scene": i}, depends_on=[f"scene_image_{i}"],
                                 group="scenes", tool="sim.video_render"))
            video_ids.append(sid); seq += 1
        stages.append(_stage(seq, "voice", "text_to_speech", "generate_speech",
                             {"script_ref": "script"}, depends_on=["script"],
                             group="audio", tool="sim.tts")); seq += 1
        stages.append(_stage(seq, "music", "music_generation", "generate_music",
                             {"mood": params.get("mood", "upbeat")}, depends_on=["story"],
                             group="audio", tool="sim.music")); seq += 1
        stages.append(_stage(seq, "edit", "video_editing", "render_video",
                             {"inputs": video_ids + ["voice", "music"]},
                             depends_on=video_ids + ["voice", "music"],
                             tool="sim.video_render")); seq += 1
        stages.append(_stage(seq, "qa", "video_editing", "validate_video",
                             {"target": "edit"}, depends_on=["edit"])); seq += 1
        stages.append(_stage(seq, "final_video", "video_editing", "render_video",
                             {"inputs": ["edit"], "final": True}, depends_on=["qa"],
                             tool="sim.video_render")); seq += 1
        if params.get("save_to"):
            stages.append(_stage(seq, "save_to_disk", "artifact_save_local", "artifact.save",
                                 {"artifact_ref": "final_video", "path": params["save_to"]},
                                 depends_on=["final_video"]))
        return {"title": "Video workflow", "capability": "text_to_video", "stages": stages}

    if task_type == "image_generation":
        prompts = params.get("prompts") or [objective]
        stages = [
            _stage(i + 1, f"image_{i+1}", "image_generation", "generate_image",
                   {"prompt": p}, group="images", tool="sim.image_generate")
            for i, p in enumerate(prompts)
        ]
        return {"title": "Image generation", "capability": "image_generation", "stages": stages}

    if task_type == "voice_generation":
        return {"title": "Voice generation", "capability": "text_to_speech",
                "stages": [_stage(1, "tts", "text_to_speech", "generate_speech",
                                  {"text": objective}, tool="sim.tts")]}

    if task_type == "speech_to_text":
        return {"title": "Transcription", "capability": "speech_to_text",
                "stages": [_stage(1, "transcribe", "speech_to_text", "transcribe_audio",
                                  {"artifact_ref": params.get("artifact_ref")})]}

    if task_type == "music_generation":
        return {"title": "Music generation", "capability": "music_generation",
                "stages": [_stage(1, "music", "music_generation", "generate_music",
                                  {"prompt": objective}, tool="sim.music")]}

    if task_type == "research":
        mode = params.get("mode", "local_corpus")
        stages = [_stage(1, "plan_queries", "text_generation", "generate_text",
                         {"prompt": f"Plan research queries for: {objective}"}, tool="sim.text_generate")]
        if mode == "web":
            stages.append(_stage(2, "web_search", "web_research", "web.search",
                                 {"objective": objective}, depends_on=["plan_queries"]))
        else:
            stages.append(_stage(2, "corpus_search", "document_research", "research.local_search",
                                 {"objective": objective, "root": params.get("root")},
                                 depends_on=["plan_queries"]))
        stages += [
            _stage(3, "synthesis", "research_synthesis", "generate_text",
                   {"prompt": f"Synthesize findings for: {objective}"}, depends_on=["corpus_search" if mode != "web" else "web_search"], tool="sim.text_generate"),
            _stage(4, "report", "report_generation", "report.markdown",
                   {"title": f"Research report: {objective[:80]}"}, depends_on=["synthesis"]),
        ]
        if params.get("save_to"):
            stages.append(_stage(5, "save_report", "artifact_save_local", "artifact.save",
                                 {"artifact_ref": "report", "path": params["save_to"]},
                                 depends_on=["report"]))
        return {"title": "Research", "capability": "research_synthesis", "stages": stages}

    if task_type == "document":
        return {"title": "Document", "capability": "report_generation",
                "stages": [
                    _stage(1, "draft", "text_generation", "generate_text",
                           {"prompt": f"Draft: {objective}"}, tool="sim.text_generate"),
                    _stage(2, "report", "report_generation", "report.markdown",
                           {"title": params.get("title", "Document")}, depends_on=["draft"]),
                ] + ([_stage(3, "save", "artifact_save_local", "artifact.save",
                             {"artifact_ref": "report", "path": params["save_to"]},
                             depends_on=["report"])] if params.get("save_to") else [])}

    if task_type in ("coding", "app_generation"):
        return {"title": "Coding task", "capability": "code_generation",
                "stages": [
                    _stage(1, "spec", "text_generation", "generate_text",
                           {"prompt": f"Write a precise spec for: {objective}"}, tool="sim.text_generate"),
                    _stage(2, "implement", "code_generation", "generate_code",
                           {"spec_ref": "spec"}, depends_on=["spec"], tool="sim.text_generate"),
                    _stage(3, "test", "testing", "run_tests", {"target": "implement"},
                           depends_on=["implement"]),
                ]}

    # text_generation + generic
    return {"title": "Text generation", "capability": "text_generation",
            "stages": [_stage(1, "generate", "text_generation", "generate_text",
                              {"prompt": objective}, tool="sim.text_generate")]}
