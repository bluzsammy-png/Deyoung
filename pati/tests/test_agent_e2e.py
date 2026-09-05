"""END-TO-END FLOW 1 (the required proof):

    Personal AI client -> PATI -> task -> Local Agent ->
    authorized hard-drive operation -> artifact/result -> PATI -> client

Simulates: "Create a folder called YouTube Project 01 in my authorized Video
Projects directory and organize today's script, images, audio and final video."
"""
from __future__ import annotations


def test_local_agent_organizes_hard_drive(server, admin, agent_factory, workspace):
    # seed today's files in the workspace (the "hard drive")
    (workspace / "script.txt").write_text("episode script")
    (workspace / "b-roll.png").write_bytes(b"\x89PNG fake image")
    (workspace / "voiceover.mp3").write_bytes(b"fake mp3 audio")
    (workspace / "final-cut.mp4").write_bytes(b"fake mp4 video")

    runner = agent_factory(workspace, name="video-pc")
    runner.start()

    # Personal AI client (SDK) submits the objective to PATI
    task = admin.submit_task(
        "Create a folder called YouTube Project 01 in my authorized workspace "
        "and organize today's script, images, audio and final video",
        task_type="filesystem_organize",
        params={"workspace": str(workspace)})
    assert len(task["stages"]) == 1

    done = admin.wait_for_task(task["id"], timeout_s=60, poll_s=0.4)
    assert done["status"] == "COMPLETED", done.get("error")

    project = workspace / "YouTube Project 01"
    assert (project / "manifest.json").exists()
    assert (project / "scripts" / "script.txt").exists()
    assert (project / "images" / "b-roll.png").exists()
    assert (project / "audio" / "voiceover.mp3").exists()
    assert (project / "video" / "final-cut.mp4").exists()

    # PATI recorded the operation + a local-reference artifact
    arts = admin.list_task_artifacts(task["id"])
    assert any(a["storage"] == "local_reference" and "manifest" in a["name"] for a in arts)

    # audit trail captured the disk operations (hash-chained, verified)
    ok, n = runner.audit.verify()
    assert ok and n > 0
    actions = [r["action"] for r in runner.audit.tail(100)]
    assert "fs.organize" in actions

    # client can read back task logs through PATI
    logs = admin.get_task_logs(task["id"])
    assert any("dispatched to worker" in l["message"] for l in logs["logs"])
    runner.stop()


def test_local_agent_blocks_unauthorized_path(server, admin, agent_factory, workspace, tmp_path):
    runner = agent_factory(workspace, name="guarded-pc")
    runner.start()

    outside = tmp_path / "outside"
    outside.mkdir()
    task = admin.submit_task("save file outside authorized roots", task_type="filesystem_organize",
                             params={"workspace": str(outside), "target_folder": "X"})
    done = admin.wait_for_task(task["id"], timeout_s=60, poll_s=0.4)
    # agent must refuse: root not authorized -> SECURITY_VIOLATION -> QUARANTINED
    assert done["status"] in ("QUARANTINED", "FAILED")
    stages = {s["name"]: s for s in done["stages"]}
    assert stages["organize_workspace"]["status"] == "FAILED"
    runner.stop()
