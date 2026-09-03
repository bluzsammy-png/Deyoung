"""Planner classification + router behavior + quota enforcement."""
from __future__ import annotations

from pati_api import planner


def test_classification():
    assert planner.classify_objective("Create a folder called YouTube Project 01 and organize my files") == "filesystem_organize"
    assert planner.classify_objective("Create a 60-second animated story") == "video_workflow"
    assert planner.classify_objective("generate an image of a sunset") == "image_generation"
    assert planner.classify_objective("research transformers architecture") == "research"
    assert planner.classify_objective("write a story about robots") == "text_generation"


def test_folder_name_extraction():
    p = planner.plan_task("filesystem_organize",
                          "Create a folder called YouTube Project 01 in my Video Projects folder",
                          {}, {})
    assert p["stages"][0]["params"]["target_folder"] == "YouTube Project 01"
    p2 = planner.plan_task("filesystem_organize",
                           'Create a folder named "My Research Stuff" and organize files',
                           {}, {})
    assert p2["stages"][0]["params"]["target_folder"] == "My Research Stuff"


def test_video_plan_parallel_groups():
    plan = planner.plan_task("video_workflow", "Create a 60-second animated story", {}, {})
    names = [s["name"] for s in plan["stages"]]
    assert "story" in names and "final_video" in names
    scenes = [s for s in plan["stages"] if s["name"].startswith("scene_image_")]
    assert len(scenes) >= 2
    assert all(s["group"] == "scenes" for s in scenes)
    # every dependency references an existing stage
    all_names = set(names)
    for s in plan["stages"]:
        assert set(s["depends_on"]) <= all_names


def test_no_free_worker_marks_waiting(server, admin):
    import time as _t
    # register a worker that cannot serve text_generation
    admin.register_worker(name="fs-only", wtype="LOCAL_WORKER", capabilities=["filesystem_read"])
    task = admin.submit_task("write a story about the sea", task_type="text_generation")
    status = ""
    for _ in range(20):
        _t.sleep(0.5)
        status = admin.get_task(task["id"])["status"]
        if status == "WAITING_FOR_RESOURCE":
            break
    assert status == "WAITING_FOR_RESOURCE", (
        "task with no capable free worker must park in WAITING_FOR_RESOURCE")
    # the error is explicit, never a silent paid fallback
    assert admin.get_task(task["id"])["error"] in (None, "")


def test_quota_blocks_when_concurrent_tasks_full(server, admin):
    from pati.errors import APIError
    admin._request("POST", "/admin/quotas/max_concurrent_tasks", json={"value": 1})
    try:
        admin.register_worker(name="qworker", wtype="LOCAL_WORKER",
                              capabilities=["filesystem_read", "report_generation",
                                            "document_research", "system_inspection",
                                            "text_generation", "research_synthesis",
                                            "artifact_save_local", "filesystem_create"])
        t1 = admin.submit_task("write a research brief about coral", task_type="research",
                               params={"mode": "local_corpus"})
        blocked = False
        try:
            admin.submit_task("write a research brief about kelp", task_type="research",
                              params={"mode": "local_corpus"})
        except APIError as e:
            blocked = e.status == 429
        assert blocked, "second concurrent task must be quota-blocked with HTTP 429"
    finally:
        admin._request("POST", "/admin/quotas/max_concurrent_tasks", json={"value": 4})
