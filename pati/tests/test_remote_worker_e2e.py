"""END-TO-END FLOW 2 (the required proof):

    Personal AI client -> PATI -> task -> REMOTE FREE WORKER (Kaggle-class GPU)
    -> artifacts -> PATI -> Personal AI client

Plus: full multipurpose video pipeline with parallel scene stages, artifact
hand-off to the Local Agent (artifact saved to authorized disk), and failure
recovery with retry.
"""
from __future__ import annotations


def test_remote_gpu_worker_text_task(server, admin, gpu_worker):
    import json as _json
    task = admin.submit_task("write a story about a lighthouse", task_type="text_generation")
    done = admin.wait_for_task(task["id"], timeout_s=60, poll_s=0.4)
    assert done["status"] == "COMPLETED", done.get("error")
    assert gpu_worker.executed, "remote worker must have executed the stage"
    stage = done["stages"][0]
    assert stage["status"] == "SUCCEEDED"
    output = stage["output"]
    if isinstance(output, str):
        output = _json.loads(output)
    assert output["simulated"] is True
    assert stage["worker_id"] == gpu_worker.worker_id


def test_full_video_pipeline_with_parallel_scenes_and_local_save(
        server, admin, gpu_worker, agent_factory, workspace):
    runner = agent_factory(workspace, name="video-pc")
    runner.start()

    final_path = workspace / "Video Projects" / "final_video.mp4"
    task = admin.submit_task(
        "Create a 60-second animated story and save the final video into my workspace",
        task_type="video_workflow",
        params={"scenes": 3, "save_to": str(final_path)})

    done = admin.wait_for_task(task["id"], timeout_s=180, poll_s=0.5)
    assert done["status"] == "COMPLETED", done.get("error")

    names = [s["name"] for s in done["stages"]]
    for expected in ["story", "script", "character_bible", "storyboard",
                     "scene_image_1", "scene_image_2", "scene_image_3",
                     "scene_video_1", "voice", "music", "edit", "qa", "final_video",
                     "save_to_disk"]:
        assert expected in names, expected

    # scenes were planned as a parallel group
    import json as _json
    plan = done["plan"]
    if isinstance(plan, str):
        plan = _json.loads(plan)
    scene_stages = [s for s in plan["stages"] if s["name"].startswith("scene_")]
    assert all(s["group"] == "scenes" for s in scene_stages)

    # artifacts flowed: remote worker -> PATI -> local disk (authorized folder)
    arts = admin.list_task_artifacts(task["id"])
    uploaded = [a for a in arts if a["storage"] == "control_plane"]
    assert len(uploaded) >= 3  # scene images/videos/voice/music artifacts
    assert final_path.exists(), "final artifact must be saved by the Local Agent"

    # the save_to_disk stage was executed by the LOCAL agent, rest by the remote worker
    runner_names = runner.audit.tail(200)
    assert any("artifact.save" in r["action"] for r in runner_names)

    runner.stop()


def test_failure_recovery_retry(server, admin):
    from tests.conftest import MockGPUWorker
    w = MockGPUWorker(server["base_url"], admin, name="flaky-gpu", fail_first_job=True)
    w.start()
    try:
        task = admin.submit_task("write a haiku about persistence",
                                 task_type="text_generation")
        done = admin.wait_for_task(task["id"], timeout_s=90, poll_s=0.4)
        assert done["status"] == "COMPLETED", done.get("error")
        assert w.failed_jobs >= 1, "first attempt must have failed (transient)"
        # the failed stage was retried automatically and then succeeded
        assert any("requeued" in l["message"]
                   for l in admin.get_task_logs(task["id"])["logs"])
    finally:
        w.stop()


def test_cancel_running_task(server, admin):
    task = admin.submit_task("write a very long story", task_type="text_generation")
    r = admin.cancel_task(task["id"])
    assert r["ok"] is True
    done = admin.get_task(task["id"])
    assert done["status"] in ("CANCELLED",)
