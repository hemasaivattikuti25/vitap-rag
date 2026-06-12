from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import sys
import os
import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from api.routes import router

app = FastAPI(title="vitap-UniOs API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
IST_OFFSET = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def _seconds_until_midnight_ist() -> float:
    """Seconds from now until next midnight IST (00:00:00)."""
    now_ist = datetime.datetime.now(IST_OFFSET)
    tomorrow = (now_ist + datetime.timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return (tomorrow - now_ist).total_seconds()


async def _run_step(name: str, *cmd: str) -> bool:
    """Run a subprocess step, stream output, return True on success."""
    print(f"[pipeline] ▶ {name} ...")
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=BACKEND_DIR,
    )
    async for line in proc.stdout:
        print(f"[pipeline]   {line.decode().rstrip()}")
    await proc.wait()
    ok = proc.returncode == 0
    print(f"[pipeline] {'✅' if ok else '❌'} {name} done (exit={proc.returncode})")
    return ok


async def run_full_rebuild():
    """
    Full 5-step rebuild pipeline:
      1. Scrape all VIT-AP pages with Playwright
      2. Remove boilerplate + embed + index into Qdrant
         (also auto-injects fees & placement facts at end)
      3. Restore faculty profiles
    """
    print("[pipeline] ═══════════════════════════════════════════")
    print("[pipeline]  VIT-AP Full Index Rebuild — START")
    print(f"[pipeline]  Time (IST): {datetime.datetime.now(IST_OFFSET).isoformat()}")
    print("[pipeline] ═══════════════════════════════════════════")

    ok1 = await _run_step(
        "Step 1/3 — Scrape VIT-AP website (Playwright)",
        sys.executable, "rebuild_index.py", "--force",
    )
    if not ok1:
        print("[pipeline] ⚠ Scrape failed — aborting rebuild.")
        return

    ok2 = await _run_step(
        "Step 2/3 — Deduplicate + embed + index (+ fees & placement facts)",
        sys.executable, "remove_boilerplate.py",
    )
    if not ok2:
        print("[pipeline] ⚠ Boilerplate/index step failed — still trying faculty...")

    ok3 = await _run_step(
        "Step 3/3 — Restore faculty profiles",
        sys.executable, "reprocess_faculty_cache.py",
    )

    print("[pipeline] ═══════════════════════════════════════════")
    print(f"[pipeline]  Rebuild {'COMPLETE ✅' if (ok1 and ok2 and ok3) else 'PARTIAL ⚠'}")
    print(f"[pipeline]  Time (IST): {datetime.datetime.now(IST_OFFSET).isoformat()}")
    print("[pipeline] ═══════════════════════════════════════════")


async def _midnight_rebuild_loop():
    """
    Waits until next midnight IST, then runs the full rebuild pipeline
    every 24 hours — automatic, no manual work needed.
    """
    wait = _seconds_until_midnight_ist()
    next_run = datetime.datetime.now(IST_OFFSET) + datetime.timedelta(seconds=wait)
    print(f"[scheduler] ⏰ First rebuild scheduled at midnight IST → {next_run.strftime('%Y-%m-%d %H:%M IST')}")
    print(f"[scheduler]    (sleeping {wait/3600:.1f} hours)")

    await asyncio.sleep(wait)

    while True:
        await run_full_rebuild()
        # Sleep exactly 24 hours for subsequent runs
        await asyncio.sleep(24 * 60 * 60)


async def _feed_refresh_loop():
    """Refresh news/events feed every 30 minutes."""
    await asyncio.sleep(3)  # let server boot
    from db.feed_store import feed_store
    while True:
        try:
            print("[feed] Refreshing news/events feed...")
            await feed_store._refresh()
            print("[feed] Feed refresh complete.")
        except Exception as e:
            print(f"[feed] Error: {e}")
        await asyncio.sleep(30 * 60)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(_feed_refresh_loop())
    asyncio.create_task(_midnight_rebuild_loop())
    nxt = datetime.datetime.now(IST_OFFSET) + datetime.timedelta(
        seconds=_seconds_until_midnight_ist()
    )
    print(
        "[main] vitap-UniOs API v2 started.\n"
        f"[main] Auto-rebuild: every midnight IST (next: {nxt.strftime('%Y-%m-%d %H:%M IST')})\n"
        "[main] Feed refresh: every 30 minutes."
    )


@app.get("/")
def read_root():
    return {"message": "vitap-UniOs API v2 — Campus Platform for VIT-AP"}


@app.post("/api/admin/rebuild")
async def trigger_rebuild():
    """
    Manual trigger endpoint — POST /api/admin/rebuild
    Kicks off the full pipeline in the background immediately.
    """
    asyncio.create_task(run_full_rebuild())
    return {"status": "rebuild started", "message": "Full index rebuild triggered manually."}
