"""Bind a published staff-reviewed design to a typed product variant atomically."""
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException
from sqlalchemy import text

from app.api.auth import require_staff
from app.api.v1.catalog import fail
from app.core.print_render import canonical, digest
from app.core.template_auth import recent_template_auth
from app.db.template_registry import RegistryRepository


def manual_policy(settings):
    origin = settings.print_template_public_origin or settings.print_template_web_origin
    if not origin:
        fail(422, 'TEMPLATE_QR_ORIGIN_REQUIRED')
    parsed = urlsplit(origin)
    development = settings.supabase_url == 'https://fhuxryfkfrvycsojkzvq.supabase.co'
    if (not parsed.hostname or parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment
        or parsed.hostname in {'your-safereturn-domain.com', 'example.com'}
        or not (parsed.scheme == 'https' or development and parsed.scheme == 'http' and parsed.hostname in {'127.0.0.1', 'localhost'})):
        fail(422, 'TEMPLATE_QR_ORIGIN_REQUIRED')
    policy = {'schema_version': 1, 'approval_mode': 'manual_print', 'renderer': 'safereturn-vector-v1', 'canonical_origin': origin.rstrip('/'), 'token_length': 43, 'token_format': 'base64url32bytes-v1'}
    return {'policy_id': str(uuid5(NAMESPACE_URL, 'safereturn.manual-print.v1:' + canonical(policy))), 'policy': policy, 'policy_sha256': digest(policy)}


def ensure_variant_template(context, settings, variant, parent):
    if parent.get('commerce_model') != 'single_qr' or not variant.get('template_key') or not settings.print_template_management_enabled:
        return variant
    require_staff(context, 'operations')
    recent_template_auth(context)
    ready = context.session.execute(text("SELECT EXISTS(SELECT 1 FROM pg_attribute WHERE attrelid=to_regclass('public.template_qa_approvals') AND attname='approval_kind' AND NOT attisdropped) AS manual_template_binding_available")).scalar_one()
    if not ready:
        fail(503, 'TEMPLATE_BINDING_UNAVAILABLE')
    try:
        RegistryRepository(context).call('manual_variant_bind', {'variant_id': str(variant['id']), 'expected': int(variant['catalog_version']), **manual_policy(settings)})
    except HTTPException as error:
        if error.status_code == 409 and isinstance(error.detail, dict) and error.detail.get('code') == 'CONFLICT':
            fail(409, 'TEMPLATE_BINDING_CONFLICT')
        raise
    return dict(context.session.execute(text('SELECT * FROM public.product_variants WHERE id=:id'), {'id': variant['id']}).mappings().one())
