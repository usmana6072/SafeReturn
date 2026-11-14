"""Policy construction and role/MFA/recency boundaries; no real DB mutations."""
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.auth import AccessError
from app.core.config import Settings
from app.services.manual_template_binding import ensure_variant_template, manual_policy


def test_manual_policy_uses_configured_public_page_origin():
    result = manual_policy(Settings(_env_file=None, print_template_web_origin='https://portal.safereturn.test'))
    assert result['policy']['canonical_origin'] == 'https://portal.safereturn.test'
    assert result['policy']['approval_mode'] == 'manual_print'
    assert len(result['policy_sha256']) == 64
    assert result == manual_policy(Settings(_env_file=None, print_template_web_origin='https://portal.safereturn.test/'))


def test_development_loopback_is_project_fenced():
    settings = Settings(_env_file=None, supabase_url='https://fhuxryfkfrvycsojkzvq.supabase.co', print_template_web_origin='http://127.0.0.1:3100')
    assert manual_policy(settings)['policy']['canonical_origin'] == 'http://127.0.0.1:3100'
    settings.supabase_url = 'https://other.supabase.co'
    with pytest.raises(HTTPException): manual_policy(settings)


@pytest.mark.parametrize('origin', [None, 'https://your-safereturn-domain.com', 'https://example.com', 'http://external.test', 'https://user:secret@portal.test', 'https://portal.test/qr-id', 'https://portal.test?next=private'])
def test_no_guessed_or_request_supplied_qr_origin(origin):
    with pytest.raises(HTTPException) as error:
        manual_policy(Settings(_env_file=None, print_template_public_origin=origin))
    assert error.value.detail['code'] == 'TEMPLATE_QR_ORIGIN_REQUIRED'


class Session:
    def __init__(self, role=True): self.info={}; self.role=role
    def execute(self, statement, params=None):
        sql=str(statement)
        if 'staff_roles' in sql:
            return SimpleNamespace(scalar_one_or_none=lambda: 1 if self.role else None)
        raise AssertionError('No database write or binding may precede failed admission')


@pytest.mark.parametrize('mfa,age,role', [(False,0,True),(True,1201,True),(True,0,False)])
def test_binding_cannot_bypass_staff_mfa_or_twenty_minutes(mfa,age,role):
    context=SimpleNamespace(email_verified=True,mfa_verified=mfa,principal=SimpleNamespace(user_id=uuid4(),session_id=uuid4(),authentication_time=int(time.time())-age),session=Session(role))
    with pytest.raises((AccessError,HTTPException)):
        ensure_variant_template(context,Settings(_env_file=None,print_template_management_enabled=True),{'template_key':'reviewed'}, {'commerce_model':'single_qr'})


def test_legacy_pair_and_unassigned_draft_do_not_auto_bind():
    settings=Settings(_env_file=None,print_template_management_enabled=True)
    variant={'template_key':'reviewed'}
    assert ensure_variant_template(None,settings,variant,{'commerce_model':'legacy_pair'}) is variant
    assert ensure_variant_template(None,settings,{'template_key':None},{'commerce_model':'single_qr'}) == {'template_key':None}

class Query:
    def __init__(self,value): self.value=value
    def scalar_one(self): return self.value
    def scalar_one_or_none(self): return self.value
    def mappings(self): return self
    def one_or_none(self): return self.value
    def one(self): return self.value
    def all(self): return self.value


class PublicationSession:
    def __init__(self, mismatch=False):
        from decimal import Decimal
        self.info={}; self.bound=False; self.mismatch=mismatch; self.calls=[]
        self.variant={'id':uuid4(),'catalog_version':1,'fulfillment_method':'pdf_label','size_mm':Decimal('30.00'),'currency_code':'PKR','template_key':'reviewed','template_version':1,'material':'vinyl'}
    def execute(self, statement, params=None):
        import json
        sql=str(statement);self.calls.append(sql)
        if 'slug,is_active' in sql: return Query({'slug':'qr-stickers','is_active':True})
        if 'product_variants WHERE product_id' in sql: return Query([self.variant])
        if 'staff_roles' in sql: return Query(1)
        if 'AS manual_template_binding_available' in sql or 'AS template_registry_available' in sql: return Query(True)
        if 'sr_template_lifecycle' in sql:
            assert params['action']=='manual_variant_bind'
            payload=json.loads(params['payload']);assert payload['variant_id']==str(self.variant['id']) and payload['expected']==1
            if self.mismatch: return Query({'error':'TEMPLATE_VARIANT_MISMATCH'})
            self.bound=True;return Query({'variant_row_version':2})
        if 'product_variants WHERE id' in sql: return Query({**self.variant,'catalog_version':2})
        if 'sr_template_catalog_type_eligible' in sql: return Query(self.bound)
        if 'product_images' in sql: return Query(1)
        raise AssertionError(sql)


@pytest.mark.parametrize('mismatch',[False,True])
def test_product_publish_wires_real_binding_before_eligibility_check(mismatch):
    from app.api.v1.catalog import publishable
    db=PublicationSession(mismatch)
    context=SimpleNamespace(session=db,email_verified=True,mfa_verified=True,principal=SimpleNamespace(user_id=uuid4(),session_id=uuid4(),authentication_time=int(time.time())-100))
    request=SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings=Settings(_env_file=None,print_template_management_enabled=True,print_template_web_origin='https://portal.safereturn.test'))))
    product={'id':uuid4(),'category_id':uuid4(),'commerce_model':'single_qr','qr_type':'lost','lifecycle_status':'published'}
    if mismatch:
        with pytest.raises(HTTPException) as error: publishable(context,request,product)
        assert error.value.detail['code']=='TEMPLATE_VARIANT_MISMATCH' and not db.bound
    else:
        publishable(context,request,product)
        assert db.bound
        assert next(i for i,s in enumerate(db.calls) if 'sr_template_lifecycle' in s)<next(i for i,s in enumerate(db.calls) if 'sr_template_catalog_type_eligible' in s)
