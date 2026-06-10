"""
Run a quick Lab 6 Enhanced smoke test without camera or web server.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import (
    ROOT, VIDEO_DIR, camera_manager,
    simulated_frame, log_image_pipeline, record_short_video,
    init_db, get_db, db_query,
)

async def main():
    log_lines = []
    status = "UNKNOWN"
    try:
        init_db()
        cam = camera_manager.register("simulated", "Demo Camera")
        log_lines.append(f"Camera registered: {cam.camera_id}")

        for i in range(2):
            frame = simulated_frame(i)
            result = await log_image_pipeline(
                frame,
                source_type="demo_script",
                device_id="simulated_camera",
                camera_id=cam.camera_id,
                note=f"demo_frame={i}",
                run_detection=False,
            )
            log_lines.append(json.dumps(
                {"image_id": result["image_id"], "event": result["event"]["event_type"]},
                ensure_ascii=False,
            ))

        video_result = record_short_video(cam.camera_id, seconds=1)
        log_lines.append(json.dumps(
            {"video_id": video_result["video_id"], "frames": video_result["frames"]},
            ensure_ascii=False,
        ))

        img_count = db_query("SELECT COUNT(*) as cnt FROM images")[0]["cnt"]
        ev_count = db_query("SELECT COUNT(*) as cnt FROM events")[0]["cnt"]
        log_lines.append(f"DB: {img_count} images, {ev_count} events")

        status = "LOCAL_PIPELINE_TEST_PASS"
    except Exception as exc:
        status = f"LOCAL_PIPELINE_TEST_FAIL: {exc}"
        log_lines.append(status)

    Path("RUN_TEST_LOG.txt").write_text(
        status + "\n" + "\n".join(log_lines), encoding="utf-8"
    )
    print(status)
    print(f"Quan sát: data/raw_images, data/processed_images, data/videos, outputs/lab6.db")

if __name__ == "__main__":
    asyncio.run(main())
