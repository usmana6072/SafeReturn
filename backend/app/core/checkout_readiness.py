"""Non-sensitive runtime admission metadata; no prices or release writes."""


def runtime_checkout_blockers(settings):
    reasons = []
    if not (settings.checkout_enabled or getattr(settings, "single_qr_checkout_enabled", False)):
        reasons.append("CHECKOUT_RUNTIME_DISABLED")
    if settings.checkout_shipping_pkr is None or (
        settings.checkout_tax_pkr is None and getattr(settings, "single_qr_checkout_tax_percent", None) is None
    ):
        reasons.append("CHECKOUT_CHARGES_UNCONFIGURED")
    return reasons
