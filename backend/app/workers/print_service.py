"""Run durable print processing with the API using a separate worker connection pool."""

import asyncio
import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.print_render import PrintUnavailable
from app.db.runtime import worker_transaction
from app.db.session import Database
from app.integrations.print_storage import PrintStore
from app.workers.printing import run_one

logger = logging.getLogger(__name__)

_print_wakeup_event: asyncio.Event | None = None


def trigger_print_worker() -> None:
    """Signal the background print worker to process pending print jobs immediately."""
    if _print_wakeup_event is not None:
        try:
            loop = getattr(_print_wakeup_event, "_loop", None)
            if loop is not None and loop.is_running():
                loop.call_soon_threadsafe(_print_wakeup_event.set)
            else:
                _print_wakeup_event.set()
        except (RuntimeError, AttributeError):
            _print_wakeup_event.set()


def cleanup_delivered_print_artifacts(
    database: Database, settings, storage: PrintStore
) -> int:
    """Find delivered orders with active print artifacts, delete their files from storage,

    and tombstone the artifacts and print jobs in the database.
    """
    cleaned = 0
    worker_id = settings.print_worker_id
    with worker_transaction(database, worker_id) as session:
        orders = (
            session.execute(
                text(
                    "SELECT order_id FROM public.sr_find_delivered_orders_with_artifacts()"
                )
            )
            .scalars()
            .all()
        )

    for oid in orders:
        with worker_transaction(database, worker_id) as session:
            artifacts = (
                session.execute(
                    text(
                        "SELECT artifact_id, object_key, print_job_id "
                        "FROM public.sr_delivery_print_cleanup(:oid)"
                    ),
                    {"oid": oid},
                )
                .mappings()
                .all()
            )

        for art in artifacts:
            try:
                storage.delete(art["object_key"])
            except (OSError, PrintUnavailable, ValueError) as error:
                logger.warning(
                    "Delivery storage deletion issue for artifact %s: %s",
                    art["artifact_id"],
                    error,
                )

            with worker_transaction(database, worker_id) as session:
                session.execute(
                    text("SELECT public.sr_delivery_print_finish(:aid)"),
                    {"aid": art["artifact_id"]},
                )
            cleaned += 1
            logger.info(
                "Delivered order %s print artifact %s deleted from storage and tombstoned",
                oid,
                art["artifact_id"],
            )

    return cleaned


@asynccontextmanager
async def print_service(settings):
    global _print_wakeup_event
    if not getattr(settings, "print_worker_enabled", True) or not getattr(
        settings, "print_enabled", False
    ):
        yield
        return
    if not (
        settings.worker_database_url
        and settings.worker_database_url.get_secret_value().strip()
    ):
        logger.warning(
            "Print processing is inactive: worker database configuration is required."
        )
        yield
        return

    configuration = settings.model_copy(
        update={
            "database_url": settings.worker_database_url,
            "print_worker_id": f"{settings.print_worker_id[:60]}:{uuid4().hex}",
        }
    )
    database = Database.from_settings(configuration)
    try:
        storage = PrintStore(configuration)
    except PrintUnavailable as error:
        if database is not None:
            database.close()
        logger.error("Print processing could not start: storage error %s", error)
        yield
        return

    stop = asyncio.Event()
    wakeup = asyncio.Event()
    _print_wakeup_event = wakeup

    async def run():
        while not stop.is_set():
            wakeup.clear()
            processed = True
            while processed and not stop.is_set():
                try:
                    processed = await asyncio.to_thread(
                        run_one, database, configuration, storage
                    )
                except (SQLAlchemyError, RuntimeError, OSError) as exc:
                    logger.error("Print processing error: %s", exc)
                    processed = False
            if not stop.is_set():
                try:
                    await asyncio.to_thread(
                        cleanup_delivered_print_artifacts, database, configuration, storage
                    )
                except (SQLAlchemyError, RuntimeError, OSError) as exc:
                    logger.error("Print cleanup error: %s", exc)
            if not stop.is_set():
                poll_seconds = getattr(configuration, "print_worker_poll_seconds", 5)
                try:
                    await asyncio.wait_for(wakeup.wait(), timeout=poll_seconds)
                except TimeoutError:
                    pass

    task = asyncio.create_task(run(), name="print-job-worker")
    try:
        yield
    finally:
        _print_wakeup_event = None
        stop.set()
        wakeup.set()
        try:
            await task
        finally:
            if database is not None:
                database.close()
