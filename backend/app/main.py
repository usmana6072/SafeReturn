from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.auth import AccessError, access_error
from app.api.v1.abuse_reports import install as install_abuse_reports
from app.api.v1.account import router as account_router
from app.api.v1.account_lifecycle import install as install_account_lifecycle
from app.api.v1.activation import router as activation_router
from app.api.v1.audit_events import router as audit_events_router
from app.api.v1.cancellations import install as install_cancellations
from app.api.v1.catalog import admin_router as admin_catalog_router
from app.api.v1.catalog import public_router as public_catalog_router
from app.api.v1.catalog_templates import install as install_catalog_templates
from app.api.v1.checkout import router as checkout_router
from app.api.v1.dashboard import install as install_dashboard
from app.api.v1.finance_reconciliation import install as install_finance_reconciliation
from app.api.v1.financial_disputes import install as install_financial_disputes
from app.api.v1.fulfillment import router as fulfillment_router
from app.api.v1.fulfillment_queries import router as fulfillment_queries_router
from app.api.v1.health import health_router
from app.api.v1.inventory import router as inventory_router
from app.api.v1.inventory_queries import router as inventory_queries_router
from app.api.v1.item_checkout import router as item_checkout_router
from app.api.v1.manufacturing_exports import install as install_manufacturing_exports
from app.api.v1.messages import router as messages_router
from app.api.v1.notification_operations import router as notification_operations_router
from app.api.v1.order_metadata import install as install_order_metadata
from app.api.v1.owner_qr import router as owner_qr_router
from app.api.v1.payments import router as payments_router
from app.api.v1.print_queries import install as install_print_queries
from app.api.v1.print_templates import install as install_print_templates
from app.api.v1.printing import router as printing_router
from app.api.v1.privacy_exports import router as privacy_exports_router
from app.api.v1.profiles import router as profiles_router
from app.api.v1.public_actions import router as public_actions_router
from app.api.v1.public_config import router as public_config_router
from app.api.v1.public_qr import router as public_qr_router
from app.api.v1.qr_lifecycle import install as install_qr_lifecycle
from app.api.v1.retention import router as retention_router
from app.api.v1.shipping_addresses import install as install_shipping_addresses
from app.api.v1.staff_directory import install as install_staff_directory
from app.api.v1.standalone_owner import router as standalone_owner_router
from app.api.v1.support_cases import router as support_cases_router
from app.api.v1.support_development import router as support_development_router
from app.api.v1.support_metadata import install as install_support_metadata
from app.api.v1.typed_inventory import router as typed_inventory_router
from app.core.auth import JWTVerifier
from app.core.config import Settings
from app.core.observability import RequestObservabilityMiddleware
from app.db.session import Database


def create_app(
    settings: Settings | None = None, *, verifier: JWTVerifier | None = None
) -> FastAPI:
    configuration = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        database = Database.from_settings(configuration)
        application.state.database = database
        application.state.jwt_verifier = verifier or JWTVerifier(configuration)
        try:
            yield
        finally:
            if database is not None:
                database.close()
            application.state.jwt_verifier.close()
            application.state.jwt_verifier = None
            application.state.database = None

    application = FastAPI(title="SafeReturn API", version="0.1.0", lifespan=lifespan)
    application.add_middleware(RequestObservabilityMiddleware)
    application.state.database = None
    application.state.jwt_verifier = None
    application.state.settings = configuration
    application.state.support_dev_implementation_digest = None
    if configuration.support_dev_enabled:
        from app.support_provisioning_cli import implementation_digest

        application.state.support_dev_implementation_digest = implementation_digest()
    application.add_exception_handler(AccessError, access_error)
    application.include_router(health_router(configuration), prefix="/api/v1")
    application.include_router(account_router, prefix="/api/v1")
    application.include_router(support_development_router, prefix="/api/v1")
    application.include_router(audit_events_router, prefix="/api/v1")
    application.include_router(public_catalog_router, prefix="/api/v1")
    application.include_router(checkout_router, prefix="/api/v1")
    application.include_router(item_checkout_router, prefix="/api/v1")
    install_shipping_addresses(application)
    application.include_router(admin_catalog_router, prefix="/api/v1")
    application.include_router(inventory_router, prefix="/api/v1")
    application.include_router(inventory_queries_router, prefix="/api/v1")
    application.include_router(typed_inventory_router, prefix="/api/v1")
    application.include_router(activation_router, prefix="/api/v1")
    application.include_router(profiles_router, prefix="/api/v1")
    application.include_router(owner_qr_router, prefix="/api/v1")
    application.include_router(standalone_owner_router, prefix="/api/v1")
    application.include_router(public_qr_router, prefix="/api/v1")
    application.include_router(payments_router, prefix="/api/v1")
    install_qr_lifecycle(application)
    install_print_queries(application)
    application.include_router(printing_router, prefix="/api/v1")
    application.include_router(fulfillment_router, prefix="/api/v1")
    application.include_router(fulfillment_queries_router, prefix="/api/v1")
    application.include_router(public_actions_router, prefix="/api/v1")
    application.include_router(public_config_router, prefix="/api/v1")
    install_abuse_reports(application)
    application.include_router(notification_operations_router, prefix="/api/v1")
    application.include_router(messages_router, prefix="/api/v1")
    application.include_router(retention_router, prefix="/api/v1")
    application.include_router(support_cases_router, prefix="/api/v1")
    install_support_metadata(application)
    application.include_router(privacy_exports_router, prefix="/api/v1")
    install_catalog_templates(application)
    install_print_templates(application)
    install_order_metadata(application)
    install_cancellations(application)
    install_financial_disputes(application)
    install_finance_reconciliation(application)
    install_manufacturing_exports(application)
    install_dashboard(application)
    install_staff_directory(application)
    install_account_lifecycle(application)
    return application


app = create_app()
