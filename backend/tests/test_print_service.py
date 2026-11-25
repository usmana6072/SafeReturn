import asyncio
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.core.config import Settings
from app.workers.print_service import (
    cleanup_delivered_print_artifacts,
    print_service,
    trigger_print_worker,
)


def test_missing_configuration_does_not_start_print_worker():
    async def run():
        with patch("app.workers.print_service.Database.from_settings") as connect:
            async with print_service(Settings(print_enabled=False)):
                pass
            connect.assert_not_called()

    asyncio.run(run())


def test_print_worker_disabled_setting_skips():
    async def run():
        with patch("app.workers.print_service.Database.from_settings") as connect:
            async with print_service(
                Settings(print_enabled=True, print_worker_enabled=False)
            ):
                pass
            connect.assert_not_called()

    asyncio.run(run())


def test_print_service_processes_and_drains_on_exit():
    async def run():
        settings = Settings(
            print_enabled=True,
            database_url="postgresql://api:secret@localhost/api",
            worker_database_url="postgresql://worker:secret@localhost/worker",
            supabase_url="https://fhuxryfkfrvycsojkzvq.supabase.co",
            supabase_storage_service_key="synthetic",
        )
        database = MagicMock()
        called = asyncio.Event()
        loop = asyncio.get_running_loop()

        def process(db, configuration, storage):
            assert db is database
            assert configuration.database_url == settings.worker_database_url
            loop.call_soon_threadsafe(called.set)
            return False

        with (
            patch(
                "app.workers.print_service.Database.from_settings",
                return_value=database,
            ),
            patch("app.workers.print_service.PrintStore"),
            patch("app.workers.print_service.run_one", side_effect=process) as step,
        ):
            async with print_service(settings):
                await asyncio.wait_for(called.wait(), timeout=5)
            step.assert_called_once()
            database.close.assert_called_once()

    asyncio.run(run())


def test_trigger_print_worker_wakes_up_loop():
    async def run():
        settings = Settings(
            print_enabled=True,
            database_url="postgresql://api:secret@localhost/api",
            worker_database_url="postgresql://worker:secret@localhost/worker",
            supabase_url="https://fhuxryfkfrvycsojkzvq.supabase.co",
            supabase_storage_service_key="synthetic",
            print_worker_poll_seconds=60,  # Long poll interval
        )
        database = MagicMock()
        call_count = 0
        second_call = asyncio.Event()
        loop = asyncio.get_running_loop()

        def process(db, configuration, storage):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                loop.call_soon_threadsafe(second_call.set)
            return False

        with (
            patch(
                "app.workers.print_service.Database.from_settings",
                return_value=database,
            ),
            patch("app.workers.print_service.PrintStore"),
            patch("app.workers.print_service.run_one", side_effect=process),
        ):
            async with print_service(settings):
                # Trigger the print worker while it is waiting
                await asyncio.sleep(0.05)
                trigger_print_worker()
                await asyncio.wait_for(second_call.wait(), timeout=5)

            assert call_count >= 2
            database.close.assert_called_once()

    asyncio.run(run())


def test_cleanup_delivered_print_artifacts():
    oid = uuid4()
    aid = uuid4()
    jid = uuid4()
    key = f"order-print/{oid}/{jid}/test.pdf"

    settings = Settings(
        print_enabled=True,
        worker_database_url="postgresql://worker:secret@localhost/worker",
        print_worker_id="test-worker",
    )
    database = MagicMock()
    session = MagicMock()
    storage = MagicMock()

    # Session queries: first find_delivered_orders, second delivery_print_cleanup, third delivery_print_finish
    def execute_mock(stmt, params=None):
        sql = str(stmt.text) if hasattr(stmt, "text") else str(stmt)
        res = MagicMock()
        if "sr_find_delivered_orders_with_artifacts" in sql:
            res.scalars.return_value.all.return_value = [oid]
        elif "sr_delivery_print_cleanup" in sql:
            res.mappings.return_value.all.return_value = [
                {"artifact_id": aid, "object_key": key, "print_job_id": jid}
            ]
        elif "sr_delivery_print_finish" in sql:
            pass
        return res

    session.execute.side_effect = execute_mock

    with patch("app.workers.print_service.worker_transaction") as wt:
        wt.return_value.__enter__.return_value = session
        cleaned = cleanup_delivered_print_artifacts(database, settings, storage)

    assert cleaned == 1
    storage.delete.assert_called_once_with(key)

