from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import sys
import os
import datetime
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("vitap")

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

BACKEND_DIR    = os.path.dirname(os.path.abspath(__file__))
IST_OFFSET     = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

# ── Allowed origins (set ALLOWED_ORIGINS env var as comma-separated list) ──
_raw_origins = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS: list[str] = (
    [o.strip() for o in _raw_origins.split(",") if o.strip()]
    if _raw_origins
    else [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
)
log.info(f"CORS allowed origins: {ALLOWED_ORIGINS}")


# ── Pipeline ────────────────────────────────────────────────────────────────

def _seconds_until_midnight_ist() -> float:
    now = datetime.datetime.now(IST_OFFSET)
    tomorrow = (now + datetime.timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return (tomorrow - now).total_seconds()


async def _run_step(name: str, *cmd: str) -> bool:
    log.info(f"[pipeline] ▶ {name}")
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=BACKEND_DIR,
        )
        async for line in proc.stdout:
            log.info(f"[pipeline]   {line.decode().rstrip()}")
        await proc.wait()
        ok = proc.returncode == 0
        log.info(f"[pipeline] {'✅' if ok else '❌'} {name} (exit={proc.returncode})")
        return ok
    except Exception as e:
        log.error(f"[pipeline] ❌ {name} crashed: {e}")
        return False


async def run_full_rebuild():
    log.info("═" * 50)
    log.info("VIT-AP Full Index Rebuild — START")
    log.info(f"Time (IST): {datetime.datetime.now(IST_OFFSET).isoformat()}")

    ok1 = await _run_step(
        "Step 1/3 — Scrape VIT-AP (Playwright)",
        sys.executable, "rebuild_index.py", "--force",
    )
    if not ok1:
        log.warning("[pipeline] Scrape failed — injecting facts only as fallback")
        await _run_step("Fallback — inject verified facts", sys.executable, "inject_all_facts.py")
        return

    await _run_step("Step 2/3 — Dedupe + embed + index", sys.executable, "remove_boilerplate.py")
    await _run_step("Step 3/3 — Restore faculty profiles", sys.executable, "reprocess_faculty_cache.py")

    log.info(f"Rebuild COMPLETE — {datetime.datetime.now(IST_OFFSET).isoformat()}")
    log.info("═" * 50)


async def _midnight_rebuild_loop():
    wait = _seconds_until_midnight_ist()
    nxt = datetime.datetime.now(IST_OFFSET) + datetime.timedelta(seconds=wait)
    log.info(f"[scheduler] Next rebuild at midnight IST → {nxt.strftime('%Y-%m-%d %H:%M IST')} ({wait/3600:.1f}h away)")
    await asyncio.sleep(wait)
    while True:
        await run_full_rebuild()
        await asyncio.sleep(24 * 60 * 60)


async def _feed_refresh_loop():
    await asyncio.sleep(5)
    try:
        from db.feed_store import feed_store
        while True:
            try:
                log.info("[feed] Refreshing news/events feed…")
                await feed_store._refresh()
                log.info("[feed] Feed refresh complete.")
            except Exception as e:
                log.error(f"[feed] Refresh error: {e}")
            await asyncio.sleep(30 * 60)
    except ImportError as e:
        log.error(f"[feed] feed_store unavailable: {e}")


# ── App lifespan (replaces deprecated @app.on_event) ───────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    asyncio.create_task(_feed_refresh_loop())
    asyncio.create_task(_midnight_rebuild_loop())
    nxt = datetime.datetime.now(IST_OFFSET) + datetime.timedelta(
        seconds=_seconds_until_midnight_ist()
    )
    log.info(
        f"vitap-UniOs API v2 started.\n"
        f"  Auto-rebuild: every midnight IST (next: {nxt.strftime('%Y-%m-%d %H:%M IST')})\n"
        f"  Feed refresh: every 30 minutes.\n"
        f"  CORS origins: {ALLOWED_ORIGINS}"
    )
    yield
    # Shutdown (nothing to clean up)
    log.info("vitap-UniOs API shutting down.")


# ── FastAPI app ─────────────────────────────────────────────────────────────
from limiter import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

app = FastAPI(
    title="vitap-UniOs API",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

# Register rate limiter on FastAPI instance
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

from api.routes import router
app.include_router(router, prefix="/api")


# ── Global exception handler — never returns 500 with a traceback ───────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error. Please try again."},
    )


# ── Health / status endpoints ───────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "vitap-UniOs API v2", "status": "ok"}


@app.get("/health")
def health():
    """Render uses this for health checks."""
    return {"status": "ok", "time_ist": datetime.datetime.now(IST_OFFSET).isoformat()}


@app.post("/api/admin/rebuild")
async def trigger_rebuild():
    """Manual rebuild trigger — POST /api/admin/rebuild"""
    asyncio.create_task(run_full_rebuild())
    return {"status": "started", "message": "Full rebuild triggered in background."}
