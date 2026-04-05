import asyncio
from apscheduler.schedulers.background import BackgroundScheduler

from config import BRIEFING_HOUR, BRIEFING_MINUTE
from briefing import BriefingEngine


def _run_briefing_sync() -> None:
    """Wrapper so APScheduler (sync) can invoke our async engine."""
    engine = BriefingEngine()
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(engine.run())
        print(f"[Scheduler] Briefing result: {result}")
    finally:
        loop.close()


scheduler = BackgroundScheduler()
scheduler.add_job(
    _run_briefing_sync,
    trigger="cron",
    hour=BRIEFING_HOUR,
    minute=BRIEFING_MINUTE,
    id="daily_briefing",
    replace_existing=True,
)
