"""Task 3.5: signed API requests, real locks and full transaction consequences.

All identities, fault triggers and state transitions live in the metadata-first
UUID rehearsal namespaces. No installed user or managed Auth row is modified.
"""

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import pytest
from sqlalchemy import event, text
from test_activation import activation as _activation
from test_activation import confirm, intent
from test_activation import inventory_context as _inventory_context
from test_profiles import contact
from test_profiles import profile as _profile

pytest_plugins = ["test_auth_guards"]
profile = _profile
activation = _activation
inventory_context = _inventory_context


def snapshot(pg, relations, **parameters):
    """One consistent statement; identifiers are internal test allowlists only."""
    fields = []
    for name, (table, predicate) in relations.items():
        fields.append(
            f"'{name}',(SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) FROM public.{table} t WHERE {predicate})"
        )
    with pg.connect() as c:
        return c.execute(
            text("SELECT jsonb_build_object(" + ",".join(fields) + ")"), parameters
        ).scalar_one()


def profiles_state(profile):
    pg, _, ids, _, _, _, _ = profile
    return snapshot(
        pg,
        {
            "lost": ("lost_item_profiles", "qr_id=ANY(CAST(:qids AS uuid[]))"),
            "ice": ("ice_profiles", "qr_id=ANY(CAST(:qids AS uuid[]))"),
            "preferences": (
                "tag_contact_preferences",
                "qr_id=ANY(CAST(:qids AS uuid[]))",
            ),
            "contacts": ("ice_contacts", "ice_qr_id=ANY(CAST(:qids AS uuid[]))"),
            "audit": ("audit_events", "target_id=ANY(CAST(:qids AS uuid[]))"),
            "pairs": ("tag_pairs", "id=ANY(CAST(:pids AS uuid[]))"),
            "qr": ("qr_codes", "pair_id=ANY(CAST(:pids AS uuid[]))"),
        },
        qids=[ids[k] for k in ("lost", "ice", "other_lost", "other_ice")],
        pids=[ids["pair"], ids["other_pair"]],
    )


def activation_state(activation, key):
    pg, _, _, _, pid, _ = activation
    return snapshot(
        pg,
        {
            "pair": ("tag_pairs", "id=:pid"),
            "qr": ("qr_codes", "pair_id=:pid"),
            "credential": ("pair_activation_credentials", "pair_id=:pid"),
            "intents": ("activation_intents", "pair_id=:pid"),
            "audit": ("audit_events", "target_id=:pid AND action='pair.activated'"),
            "outbox": (
                "notification_outbox",
                "aggregate_id=:pid AND event_type='pair.activated'",
            ),
            "idempotency": (
                "idempotency_records",
                "operation='pair.activate' AND idempotency_key=:key",
            ),
        },
        pid=pid,
        key=key,
    )


@contextmanager
def fault(pg, table, timing, condition, *, deferred=False):
    # Rehearsal owns these schemas; never install failure hooks in public.
    assert pg.schema.startswith("sr15_")
    assert table in {"audit_events", "qr_codes"}
    assert timing in {"BEFORE INSERT", "AFTER INSERT", "AFTER UPDATE"}
    name = "sr35_fault_" + uuid.uuid4().hex
    with pg.connect() as c:
        c.execute(
            text(
                f"CREATE FUNCTION public.{name}() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Task 3.5 injected failure' USING ERRCODE='23514'; END $$"
            )
        )
        c.execute(
            text(
                f"CREATE {'CONSTRAINT ' if deferred else ''}TRIGGER {name} {timing} ON public.{table} "
                f"{'DEFERRABLE INITIALLY DEFERRED ' if deferred else ''}FOR EACH ROW WHEN ({condition}) EXECUTE FUNCTION public.{name}()"
            )
        )
        c.commit()
    try:
        yield
    finally:
        with pg.connect() as c:
            c.execute(text(f"DROP TRIGGER {name} ON public.{table}"))
            c.execute(text(f"DROP FUNCTION public.{name}()"))
            c.commit()


@contextmanager
def synchronize(pg, marker):
    """Wait at the actual SQL command on two distinct PostgreSQL connections."""
    barrier, mutex, backends = threading.Barrier(2), threading.Lock(), set()

    def before(connection, _cursor, statement, _parameters, _context, _many):
        if marker in statement:
            with mutex:
                # A session pooler's protocol PID need not be the server PID.
                backends.add(
                    connection.execute(text("SELECT pg_backend_pid()")).scalar_one()
                )
            barrier.wait(timeout=15)

    event.listen(pg.engine, "before_cursor_execute", before)
    try:
        yield backends
    finally:
        event.remove(pg.engine, "before_cursor_execute", before)


def race(pg, marker, operations):
    warm_connections(pg)
    with synchronize(pg, marker) as backends, ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(operation) for operation in operations]
        results = [future.result(timeout=40) for future in futures]
    assert len(backends) == 2, "Race must use independent PostgreSQL sessions"
    return results


def warm_connections(pg):
    # Finish remote connection establishment before measuring SQL contention.
    # Holding two transactions also proves the pooler assigned distinct servers.
    with pg.connect() as first, pg.connect() as second:
        assert (
            first.execute(text("SELECT pg_backend_pid()")).scalar_one()
            != second.execute(text("SELECT pg_backend_pid()")).scalar_one()
        )


def blocked_request(pg, admin_change, marker, operation):
    """Commit an administrative fixture change only after proving DB contention."""
    warm_connections(pg)
    ready, backend = threading.Event(), []

    def before(connection, _cursor, statement, _parameters, _context, _many):
        if marker in statement:
            backend.append(
                connection.execute(text("SELECT pg_backend_pid()")).scalar_one()
            )
            ready.set()

    with ThreadPoolExecutor(max_workers=1) as pool, pg.connect() as c:
        blocker = c.execute(text("SELECT pg_backend_pid()")).scalar_one()
        admin_change(c)
        event.listen(pg.engine, "before_cursor_execute", before)
        try:
            future = pool.submit(operation)
            assert ready.wait(timeout=15), "Request did not reach its protected lock"
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                if (
                    blocker
                    in c.execute(
                        text("SELECT pg_blocking_pids(:pid)"), {"pid": backend[0]}
                    ).scalar_one()
                ):
                    break
                time.sleep(0.025)
            else:
                raise AssertionError(
                    "Expected actual row-lock contention was not observed"
                )
        finally:
            c.commit()
            event.remove(pg.engine, "before_cursor_execute", before)
        return future.result(timeout=40)


@pytest.mark.parametrize("actor", ["a", "operations"])
@pytest.mark.parametrize(
    "resource",
    ["lost", "ice", "contact_create", "contact_edit", "contact_delete", "preferences"],
)
def test_foreign_customer_and_staff_writes_leave_all_owner_state_unchanged(
    profile, actor, resource
):
    _, wf, _, _, request, _, _ = profile
    created = request("POST", "contacts", contact(published=False))
    assert created.status_code == 201
    cid = created.json()["contact_id"]
    operations = {
        "lost": ("PUT", "lost", {"item_label": "Foreign mutation"}, 0, ""),
        "ice": ("PUT", "ice", {"medical_notes": "Foreign private note"}, 1, ""),
        "contact_create": ("POST", "contacts", contact(published=False), 1, ""),
        "contact_edit": ("PATCH", "contacts", {"published": False}, 1, f"/{cid}"),
        "contact_delete": ("DELETE", "contacts", None, 1, f"/{cid}"),
        "preferences": ("PUT", "preferences", {"whatsapp_enabled": False}, 0, ""),
    }
    method, kind, body, version, suffix = operations[resource]
    before = profiles_state(profile)
    response = request(
        method, kind, body, version=version, suffix=suffix, actor=wf[actor]
    )
    assert response.status_code == 404, response.text
    assert response.headers["cache-control"] == "no-store"
    assert profiles_state(profile) == before


@pytest.mark.parametrize("kind", ["lost", "ice", "contacts", "preferences"])
def test_wrong_purpose_writes_do_not_create_or_modify_profiles(profile, kind):
    request = profile[4]
    method, body = {
        "lost": ("PUT", {"item_label": "Wrong purpose"}),
        "ice": ("PUT", {"display_name": "Wrong purpose"}),
        "contacts": ("POST", contact(published=False)),
        "preferences": ("PUT", {"whatsapp_enabled": False}),
    }[kind]
    before = profiles_state(profile)
    result = request(
        method, kind, body, tag="ice" if kind in ("lost", "preferences") else "lost"
    )
    assert result.status_code == 404
    assert profiles_state(profile) == before


@pytest.mark.parametrize("method", ["PATCH", "DELETE"])
def test_contact_identifier_cannot_be_moved_to_another_owned_ice_qr(profile, method):
    request = profile[4]
    cid = request("POST", "contacts", contact(published=False)).json()["contact_id"]
    before = profiles_state(profile)
    result = request(
        method,
        "contacts",
        {"published": False} if method == "PATCH" else None,
        suffix=f"/{cid}",
        tag="other_ice",
    )
    assert result.status_code == 404
    assert profiles_state(profile) == before


@pytest.mark.parametrize(
    "resource",
    ["ice", "contact_create", "contact_edit", "contact_delete", "preferences"],
)
def test_audit_failure_rolls_back_encrypted_fields_consent_and_versions(
    profile, resource
):
    pg, _, ids, _, request, _, _ = profile
    cid = None
    if resource in ("contact_edit", "contact_delete"):
        cid = request("POST", "contacts", contact(published=False)).json()["contact_id"]
    method, kind, body, version, suffix, action = {
        "ice": (
            "PUT",
            "ice",
            {"medical_notes": "Rollback private note", "display_name": "Draft"},
            0,
            "",
            "profile.ice.updated",
        ),
        "contact_create": (
            "POST",
            "contacts",
            contact(),
            0,
            "",
            "profile.ice_contact.updated",
        ),
        "contact_edit": (
            "PATCH",
            "contacts",
            contact(phone="+923009876543"),
            1,
            f"/{cid}",
            "profile.ice_contact.updated",
        ),
        "contact_delete": (
            "DELETE",
            "contacts",
            None,
            1,
            f"/{cid}",
            "profile.ice_contact.removed",
        ),
        "preferences": (
            "PUT",
            "preferences",
            {
                "whatsapp_enabled": True,
                "whatsapp_phone": "+923001234567",
                "public_disclosure_consent": True,
                "consent_version": "wa-public-v1",
            },
            0,
            "",
            "profile.whatsapp.updated",
        ),
    }[resource]
    target = ids["lost"] if resource == "preferences" else ids["ice"]
    before = profiles_state(profile)
    with fault(
        pg,
        "audit_events",
        "BEFORE INSERT",
        f"NEW.target_id='{target}'::uuid AND NEW.action='{action}'",
    ):
        failed = request(method, kind, body, version=version, suffix=suffix)
        assert failed.status_code == 503, failed.text
        assert "Rollback private note" not in failed.text and "+923" not in failed.text
        assert profiles_state(profile) == before
    retry = request(method, kind, body, version=version, suffix=suffix)
    assert retry.status_code in (200, 201, 204), retry.text
    after = profiles_state(profile)
    assert len(after["audit"]) == len(before["audit"]) + 1
    current = request("GET", "preferences" if resource == "preferences" else "ice")
    assert current.json()["version"] == version + 1


@pytest.mark.parametrize("scenario", ["lost", "ice_contact", "last_contact_slot"])
def test_concurrent_existing_versions_have_one_winner_without_lost_updates(
    profile, scenario
):
    pg, _, _, _, request, _, _ = profile
    if scenario == "lost":
        assert request("PUT", "lost", {"item_label": "Original"}).status_code == 200
        version = 1
        operations = [
            lambda label=label: request(
                "PUT", "lost", {"item_label": label}, version=version
            )
            for label in ("First", "Second")
        ]
    elif scenario == "ice_contact":
        assert request("PUT", "ice", {"display_name": "Original"}).status_code == 200
        version = 1
        operations = [
            lambda: request("PUT", "ice", {"display_name": "Changed"}, version=version),
            lambda: request(
                "POST", "contacts", contact(published=False), version=version
            ),
        ]
    else:
        for version in (0, 1):
            assert (
                request(
                    "POST", "contacts", contact(published=False), version=version
                ).status_code
                == 201
            )
        version = 2
        operations = [
            lambda: request(
                "POST", "contacts", contact(published=False), version=version
            )
        ] * 2
    before = profiles_state(profile)
    results = race(pg, "sr_lock_profile_qr", operations)
    assert sorted(r.status_code for r in results) in ([200, 412], [201, 412])
    after = profiles_state(profile)
    assert len(after["audit"]) == len(before["audit"]) + 1
    assert (
        request("GET", "lost" if scenario == "lost" else "ice").json()["version"]
        == version + 1
    )
    if scenario == "last_contact_slot":
        assert len(request("GET", "contacts").json()["contacts"]) == 3
    if scenario == "lost":
        winner = next(r for r in results if r.status_code == 200)
        assert (
            request("GET", "lost").json()["item_label"] == winner.json()["item_label"]
        )


@pytest.mark.parametrize("separate_pair", [False, True])
def test_independent_resources_save_concurrently_without_cross_writes(
    profile, separate_pair
):
    pg, _, _, _, request, _, _ = profile
    results = race(
        pg,
        "sr_lock_profile_qr",
        [
            lambda: request("PUT", "lost", {"item_label": "First pair Lost"}),
            lambda: request(
                "PUT",
                "ice",
                {"display_name": "Independent ICE"},
                tag="other_ice" if separate_pair else "ice",
            ),
        ],
    )
    assert [r.status_code for r in results] == [200, 200]
    assert request("GET", "lost").json()["version"] == 1
    assert (
        request("GET", "ice", tag="other_ice" if separate_pair else "ice").json()[
            "version"
        ]
        == 1
    )
    assert request("GET", "lost", tag="other_lost").json()["version"] == 0
    assert (
        request("GET", "ice", tag="ice" if separate_pair else "other_ice").json()[
            "version"
        ]
        == 0
    )
    assert request("GET", "preferences").json()["version"] == 0


@pytest.mark.parametrize(
    "scenario", ["two_actors", "same_request", "different_intents_same_key"]
)
def test_activation_races_commit_one_owner_and_one_set_of_side_effects(
    activation, scenario
):
    pg, wf, _, client, pid, _ = activation
    first = intent(activation).json()["intent_id"]
    second_actor = "b" if scenario == "two_actors" else "a"
    second = (
        first
        if scenario == "same_request"
        else intent(activation, actor=second_actor).json()["intent_id"]
    )
    key = uuid.uuid4().hex
    results = race(
        pg,
        "sr_confirm_activation",
        [
            lambda: confirm(activation, first, key=key),
            lambda: confirm(activation, second, actor=second_actor, key=key),
        ],
    )
    assert sorted(r.status_code for r in results) == (
        [201, 201] if scenario == "same_request" else [201, 409]
    )
    state = activation_state(activation, key)
    assert state["pair"][0]["ownership_status"] == "active"
    assert len(state["qr"]) == 2 and all(
        q["public_status"] == "active" for q in state["qr"]
    )
    assert state["credential"][0]["status"] == "consumed"
    assert sum(i["state"] == "consumed" for i in state["intents"]) == 1
    assert len(state["audit"]) == len(state["outbox"]) == 1
    assert len(state["idempotency"]) == (2 if scenario == "two_actors" else 1)
    winner = "a" if results[0].status_code == 201 else second_actor
    assert state["pair"][0]["owner_user_id"] == str(wf[winner])
    assert state["outbox"][0]["recipient_user_id"] == str(wf[winner])
    if scenario == "same_request":
        assert results[0].json() == results[1].json()
    if scenario == "two_actors":
        loser = "b" if winner == "a" else "a"
        assert (
            client.get(
                f"/api/v1/me/tag-pairs/{pid}", headers=activation[2](wf[loser])
            ).status_code
            == 404
        )


@pytest.mark.parametrize("stage", ["child", "audit", "commit"])
def test_activation_faults_roll_back_both_tags_intent_credential_and_idempotency(
    activation, stage
):
    pg, _, _, _, pid, _ = activation
    iid, key = intent(activation).json()["intent_id"], uuid.uuid4().hex
    before = activation_state(activation, key)
    table, timing, condition = (
        (
            "qr_codes",
            "AFTER UPDATE",
            f"NEW.pair_id='{pid}'::uuid AND NEW.tag_type='ice' AND NEW.public_status='active'",
        )
        if stage == "child"
        else (
            "audit_events",
            "AFTER INSERT" if stage == "commit" else "BEFORE INSERT",
            f"NEW.target_id='{pid}'::uuid AND NEW.action='pair.activated'",
        )
    )
    with fault(pg, table, timing, condition, deferred=stage == "commit"):
        failed = confirm(activation, iid, key=key)
        assert failed.status_code == 503, failed.text
        assert activation_state(activation, key) == before
    activated = confirm(activation, iid, key=key)
    assert activated.status_code == 201, activated.text
    assert confirm(activation, iid, key=key).json() == activated.json()
    after = activation_state(activation, key)
    assert len(after["audit"]) == len(after["outbox"]) == len(after["idempotency"]) == 1


@pytest.mark.parametrize("change", ["dispute", "retire"])
def test_waiting_editor_rechecks_pair_state_and_current_identity(profile, change):
    pg, _, ids, _, request, _, _ = profile
    assert (
        request("PUT", "lost", {"item_label": "Preserved original"}).status_code == 200
    )
    before = profiles_state(profile)
    replacement = uuid.uuid4()

    def mutation(c):
        c.execute(text("SELECT id FROM tag_pairs WHERE id=:pair FOR UPDATE"), ids)
        if change == "dispute":
            c.execute(
                text("UPDATE tag_pairs SET ownership_status='disputed' WHERE id=:pair"),
                ids,
            )
        else:
            c.execute(
                text(
                    "UPDATE qr_codes SET is_current=false,public_status='revoked',revoked_at=now() WHERE id=:lost"
                ),
                ids,
            )
            c.execute(
                text(
                    "INSERT INTO qr_codes(id,pair_id,tag_type,serial_number,public_token,ecc_level,public_status,replaces_qr_id) VALUES(:new,:pair,'lost',:serial,:token,'Q','active',:lost)"
                ),
                {
                    **ids,
                    "new": replacement,
                    "serial": replacement.hex,
                    "token": replacement.hex + uuid.uuid4().hex,
                },
            )

    result = blocked_request(
        pg,
        mutation,
        "sr_lock_profile_qr",
        lambda: request("PUT", "lost", {"item_label": "Must not overwrite"}, version=1),
    )
    assert result.status_code == 404, result.text
    after = profiles_state(profile)
    for kind in ("lost", "ice", "contacts", "preferences", "audit"):
        assert after[kind] == before[kind]
    if change == "retire":
        assert request("GET", "lost").status_code == 404
        assert len([q for q in after["qr"] if q["is_current"]]) == 4


def test_waiting_activation_cannot_override_a_committed_dispute(activation):
    pg, _, _, _, pid, _ = activation
    iid, key = intent(activation).json()["intent_id"], uuid.uuid4().hex

    def mutation(c):
        c.execute(
            text("UPDATE tag_pairs SET ownership_status='disputed' WHERE id=:pid"),
            {"pid": pid},
        )

    response = blocked_request(
        pg, mutation, "sr_confirm_activation", lambda: confirm(activation, iid, key=key)
    )
    assert response.status_code == 409, response.text
    state = activation_state(activation, key)
    assert state["pair"][0]["owner_user_id"] is None
    assert all(q["public_status"] == "unactivated" for q in state["qr"])
    assert state["credential"][0]["status"] == "unused"
    assert state["intents"][0]["state"] == "pending"
    assert state["audit"] == state["outbox"] == []
    assert state["idempotency"][0]["response_status"] == 409


def test_foreign_intent_denial_cannot_poison_the_owners_same_idempotency_key(
    activation,
):
    iid, key = intent(activation).json()["intent_id"], uuid.uuid4().hex
    denied = confirm(activation, iid, actor="b", key=key)
    assert denied.status_code == 409
    assert "pair_id" not in denied.json() and "qr_codes" not in denied.json()
    accepted = confirm(activation, iid, actor="a", key=key)
    assert accepted.status_code == 201, accepted.text
    assert confirm(activation, iid, actor="b", key=key).status_code == 409
    assert confirm(activation, iid, actor="a", key=key).json() == accepted.json()
    state = activation_state(activation, key)
    assert len(state["idempotency"]) == 2
    assert len(state["audit"]) == len(state["outbox"]) == 1


def test_pair_detail_returns_concealed_not_found_if_ownership_is_revoked_after_guard(
    profile, guarded
):
    pg, _, ids, client, _, _, uid = profile
    warm_connections(pg)
    revoked = threading.Event()

    def after(_connection, _cursor, statement, _parameters, _context, _many):
        sql = " ".join(statement.split())
        if (
            not revoked.is_set()
            and sql.startswith("SELECT 1 FROM")
            and ".tag_pairs WHERE id=" in sql
        ):
            revoked.set()
            # Simulate an independent, authorized revocation in the test namespace,
            # committed after the guard SELECT but before the representation read.
            with pg.connect() as c:
                c.execute(
                    text(
                        "UPDATE tag_pairs SET owner_user_id=NULL,ownership_status='revoked',revoked_at=now() WHERE id=:pair"
                    ),
                    ids,
                )
                c.commit()

    event.listen(pg.engine, "after_cursor_execute", after)
    try:
        result = client.get(
            f"/api/v1/me/tag-pairs/{ids['pair']}", headers=guarded[4](uid)
        )
    finally:
        event.remove(pg.engine, "after_cursor_execute", after)
    assert revoked.is_set(), "Guard/read interleaving was not exercised"
    assert result.status_code == 404, result.text
    assert result.headers["cache-control"] == "no-store"
