"""Explicitly approved synthetic LOCAL PostgreSQL; no live finance release."""
import os
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine,text
from independent_finance_local import local_cluster
from independent_finance_fixtures import actor, claims, make_order, seed, stock

pytestmark=pytest.mark.skipif(os.environ.get('SAFERETURN_INDEPENDENT_FINANCE_REHEARSAL')!='1',reason='Isolated finance rehearsal approval required')

@pytest.fixture(scope='module')
def cluster():
    with local_cluster() as cluster:
        yield cluster


def test_migration_installs_without_runtime_grants(cluster):
    url,_,_=cluster
    engine=create_engine(url,hide_parameters=True)
    try:
        with engine.connect() as c:
            assert c.execute(text("SELECT has_function_privilege('safereturn_api','public.sr_independent_finance_snapshot(uuid,uuid)','EXECUTE')")).scalar_one() is False
            assert c.execute(text('SELECT enabled FROM public.single_checkout_release')).scalar_one() is False
            assert c.execute(text('SELECT count(*) FROM public.payment_reviews')).scalar_one()==0
    finally:engine.dispose()


@pytest.fixture
def case(cluster):
    url, connect, _ = cluster
    name = 'finance_case_' + uuid4().hex
    with connect() as c:
        c.autocommit = True
        c.execute('CREATE DATABASE ' + name + ' TEMPLATE finance_template')
    engine = create_engine(url.set(database=name), hide_parameters=True)
    try:
        with engine.begin() as c:
            # Grants ONLY in this disposable test database, never in the migration.
            c.execute(text('GRANT EXECUTE ON FUNCTION public.sr_independent_finance_snapshot(uuid,uuid), public.sr_independent_finance_review(uuid,numeric,uuid,text,boolean,numeric,text,bytea,text), public.sr_independent_finance_retry(uuid,numeric,uuid) TO safereturn_api'))
        yield seed(SimpleNamespace(connect=engine.connect))
    finally:
        engine.dispose()


def review(case, order, *, decision='verify', bank=True, amount=None, fingerprint=None, age=0, barrier=None):
    pg, staff, _, sid, _ = case
    with pg.connect() as c:
        actor(c, staff)
        c.execute(text('SET LOCAL ROLE safereturn_api'))
        if barrier:
            barrier.wait(timeout=20)
        result = c.execute(text('SELECT public.sr_independent_finance_review(:sid,:auth,:aid,:decision,:bank,:amount,:currency,:fingerprint,:note)'), {
            'sid':sid, 'auth':time.time()-age, 'aid':order[1], 'decision':decision, 'bank':bank,
            'amount':(order[2] if amount is None else amount) if decision=='verify' else None,
            'currency':'PKR' if decision=='verify' else None,
            'fingerprint':(fingerprint or os.urandom(32)) if decision=='verify' else None,
            'note':'Synthetic local finance review',
        }).scalar_one()
        c.commit()
        return result


def snapshot(case, order):
    pg, staff, _, sid, _ = case
    with pg.connect() as c:
        actor(c, staff)
        c.execute(text('SET LOCAL ROLE safereturn_api'))
        result=c.execute(text('SELECT public.sr_independent_finance_snapshot(:sid,:oid)'), {'sid':sid,'oid':order[0]}).scalar_one()
        c.commit()
        return result


def test_real_sql_settlement_preserves_logical_identity(case):
    order=make_order(case, kinds=('lost','ice'), copies=3)
    stock(case,'lost')
    stock(case,'ice')
    before=snapshot(case,order)
    assert 'REVIEW_PENDING' in before['signals']
    assert len(claims(case,order[0]))==0
    assert review(case,order)['state']=='verified'
    original=claims(case,order[0])
    assert len(original)==2
    after=snapshot(case,order)
    assert after['payment_status']=='verified'
    assert after['allocation']['state']=='allocated'
    assert after['signals']==[]
    assert len(after['reviews'])==1
    assert review(case,order)['error']=='PAYMENT_CLOSED'
    assert claims(case,order[0])==original


@pytest.mark.parametrize('kwargs', [{'age':301},{'bank':False},{'amount':1}])
def test_invalid_settlement_never_allocates(case, kwargs):
    order=make_order(case)
    stock(case)
    assert 'error' in review(case,order,**kwargs)
    assert claims(case,order[0])==[]
    assert snapshot(case,order)['payment_status']!='verified'


def test_review_and_reject(case):
    order=make_order(case)
    assert review(case,order,decision='request_more_info',bank=False)['state']=='under_review'
    assert review(case,order,decision='reject',bank=False)['state']=='rejected'
    assert len(snapshot(case,order)['reviews'])==2
    assert claims(case,order[0])==[]


def test_concurrent_verification_has_one_winner(case):
    order=make_order(case)
    stock(case)
    barrier=Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _: review(case,order,barrier=barrier),range(2)))
    assert sum(r.get('state')=='verified' for r in results)==1
    assert len(claims(case,order[0]))==1
    assert len(snapshot(case,order)['reviews'])==1
