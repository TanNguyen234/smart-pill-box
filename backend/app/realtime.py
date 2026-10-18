"""Single-process realtime clock poller for the course demo.

Uses one shared SQLAlchemy engine, a persisted per-device cursor, and the
same minute-processing function as manual simulation. No external scheduler.
Run uvicorn with one worker; multiple worker processes need a DB-level lease.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models import SimulationState

logger = logging.getLogger(__name__)
VN_TZ = timezone(timedelta(hours=7))
MAX_REPLAY_MINUTES = 24 * 60


def tick_realtime(app, *, now: datetime | None = None) -> bool:
    """Process real Vietnamese minutes, including missed minutes since the last tick.

    The clock is persisted in SQLite, so restarting the backend resumes from
    the last checkpoint (up to one day of missed minutes).
    """
    from app.main import parse_virtual_clock, process_clock_minute

    current = now if now is not None else app.state.now_provider()
    if current.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    current = current.astimezone(VN_TZ)
    current_minute = current.replace(second=0, microsecond=0)

    with app.state.clock_lock:
        with app.state.session_factory.begin() as db:
            state = db.scalar(
                select(SimulationState).where(SimulationState.device_id == "SIM-001")
            )
            if state is None or state.clock_mode != "REALTIME":
                return False

            previous = parse_virtual_clock(state.virtual_clock)
            previous_minute = previous.replace(second=0, microsecond=0)
            if previous > current:
                # Never replay the clock backwards when host time is adjusted.
                return False

            pending_minutes = int((current_minute - previous_minute).total_seconds() // 60)
            if pending_minutes > MAX_REPLAY_MINUTES:
                logger.warning("Realtime scheduler recovering only the latest %s minutes", MAX_REPLAY_MINUTES)
                previous_minute = current_minute - timedelta(minutes=MAX_REPLAY_MINUTES)
                pending_minutes = MAX_REPLAY_MINUTES

            if pending_minutes > 0:
                for i in range(1, pending_minutes + 1):
                    process_clock_minute(
                        db, previous_minute + timedelta(minutes=i), state.patient_id,
                        clock_mode="REALTIME",
                    )
            else:
                # If a schedule was added during the current minute, pick it
                # up without waiting for the next day. Processing is idempotent.
                process_clock_minute(db, current_minute, state.patient_id, clock_mode="REALTIME")

            state.virtual_clock = current.isoformat(timespec="seconds")
            return True


async def realtime_clock_worker(app) -> None:
    """Runs even with no browser or mobile app connected."""
    while True:
        try:
            await asyncio.to_thread(tick_realtime, app)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Realtime schedule check failed; retrying")
        await asyncio.sleep(3)
