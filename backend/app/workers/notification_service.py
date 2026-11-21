"""Run durable email processing with the API using a separate worker connection pool."""

import asyncio
import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError

from app.db.session import Database
from app.workers.notifications import (
    NotificationProviderError,
    ResendProvider,
    process_one,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def notification_service(settings):
    if not settings.notification_worker_enabled:
        yield
        return
    if not (
        settings.worker_database_url
        and settings.worker_database_url.get_secret_value().strip()
        and settings.resend_api_key
        and settings.resend_api_key.get_secret_value().strip()
        and settings.notification_from_email
        and settings.notification_from_email.strip()
    ):
        logger.warning(
            "Customer email processing is inactive: worker database and Resend configuration are required."
        )
        yield
        return
    configuration = settings.model_copy(
        update={
            "database_url": settings.worker_database_url,
            "notification_worker_id": f"{settings.notification_worker_id[:60]}:{uuid4().hex}",
        }
    )
    database = Database.from_settings(configuration)
    try:
        provider = ResendProvider(configuration)
    except NotificationProviderError:
        if database is not None:
            database.close()
        logger.error(
            "Customer email processing could not start: check Resend sender configuration."
        )
        yield
        return
    stop = asyncio.Event()

    async def run():
        while not stop.is_set():
            try:
                processed = await asyncio.to_thread(
                    process_one, database, configuration, provider
                )
            except (SQLAlchemyError, NotificationProviderError):
                logger.error(
                    "Customer email processing failed; check worker permissions, schema and configuration."
                )
                processed = False
            if not processed:
                try:
                    await asyncio.wait_for(stop.wait(), timeout=5)
                except TimeoutError:
                    pass

    task = asyncio.create_task(run(), name="customer-email-delivery")
    try:
        yield
    finally:
        stop.set()
        try:
            await task
        finally:
            database.close()
