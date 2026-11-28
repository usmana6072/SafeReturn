import pytest
from pydantic import ValidationError

from app.api.v1.catalog import VariantRequest


def variant(size):
    return {
        "sku": "MIN-SIZE",
        "name": "Minimum QR symbol",
        "size_mm": str(size),
        "fulfillment_method": "pdf_label",
    }


@pytest.mark.parametrize("size", [15, 25, 100])
def test_pdf_variant_accepts_supported_qr_symbol_sizes(size):
    assert VariantRequest.model_validate(variant(size)).size_mm == size


@pytest.mark.parametrize("size", [0, 14.99, 100.01, -1])
def test_pdf_variant_rejects_qr_symbol_sizes_outside_template_range(size):
    with pytest.raises(ValidationError):
        VariantRequest.model_validate(variant(size))
