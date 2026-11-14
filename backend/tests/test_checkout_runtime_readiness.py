from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.api.auth import AccessError
from app.core.checkout_readiness import runtime_checkout_blockers
from app.core.config import Settings
from app.api.v1.checkout import configured


def test_independent_runtime_does_not_enable_legacy_checkout():
    settings = Settings(single_qr_checkout_enabled=True, checkout_shipping_pkr="100.00", single_qr_checkout_tax_percent="5")
    assert runtime_checkout_blockers(settings) == []
    assert settings.checkout_enabled is False and settings.checkout_tax_pkr is None
    with pytest.raises(AccessError) as error:
        configured(SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=settings))))
    assert error.value.status == 503


def test_missing_config_reports_both_blockers():
    assert runtime_checkout_blockers(Settings()) == ["CHECKOUT_RUNTIME_DISABLED", "CHECKOUT_CHARGES_UNCONFIGURED"]


@pytest.mark.parametrize("rate", ["-1", "100.01", "NaN", "Infinity", "1.00001"])
def test_invalid_tax_rate_is_rejected(rate):
    with pytest.raises(ValidationError):
        Settings(single_qr_checkout_tax_percent=rate)
