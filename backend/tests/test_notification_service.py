import asyncio
from unittest.mock import MagicMock, patch

from app.core.config import Settings
from app.workers.notification_service import notification_service


def test_missing_configuration_does_not_start_a_worker():
    async def run():
        with patch(
            "app.workers.notification_service.Database.from_settings"
        ) as connect:
            async with notification_service(Settings()):
                pass
            connect.assert_not_called()

    asyncio.run(run())


def test_service_uses_worker_connection_and_drains_before_closing():
    async def run():
        settings = Settings(
            database_url="postgresql://api:secret@localhost/api",
            worker_database_url="postgresql://worker:secret@localhost/worker",
            brevo_api_key="synthetic",
            notification_from_email="SafeReturn <hello@example.test>",
        )
        database = MagicMock()
        called = asyncio.Event()
        loop = asyncio.get_running_loop()

        def process(db, configuration, provider):
            assert db is database
            assert configuration.database_url == settings.worker_database_url
            loop.call_soon_threadsafe(called.set)
            return False

        with (
            patch(
                "app.workers.notification_service.Database.from_settings",
                return_value=database,
            ),
            patch("app.workers.notification_service.BrevoProvider"),
            patch(
                "app.workers.notification_service.process_one", side_effect=process
            ) as step,
        ):
            async with notification_service(settings):
                await asyncio.wait_for(called.wait(), timeout=5)
            step.assert_called_once()
            database.close.assert_called_once()

    asyncio.run(run())


def test_dedicated_worker_configuration_disables_embedded_service():
    async def run():
        with patch(
            "app.workers.notification_service.Database.from_settings"
        ) as connect:
            async with notification_service(
                Settings(notification_worker_enabled=False)
            ):
                pass
            connect.assert_not_called()

    asyncio.run(run())
