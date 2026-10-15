"""Actual account endpoints, signed JWTs, PostgreSQL commits/RLS and lost-update races."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import text
from test_auth_guards import guarded  # noqa: F401 -- shared isolated PostgreSQL fixture


@pytest.fixture
def account(guarded):  # noqa: F811 -- pytest fixture injection
    pg, _, _, sessions, headers, client = guarded
    uid, sid = uuid.uuid4(), uuid.uuid4()
    with pg.connect() as c:
        c.execute(
            text("INSERT INTO auth.users(id,email_confirmed_at) VALUES(:uid,now())"),
            {"uid": uid},
        )
        c.execute(
            text("INSERT INTO auth.sessions(id,user_id,aal) VALUES(:sid,:uid,'aal1')"),
            {"sid": sid, "uid": uid},
        )
        c.commit()
    sessions[uid] = sid
    return pg, uid, headers(uid), client


def edit(client, headers, version, body):
    return client.request(
        "PATCH",
        "/api/v1/me",
        headers={**headers, "If-Match": '"' + version + '"'},
        json=body,
    )


def test_empty_summary_has_no_get_side_effect_and_no_auth_internals(account):
    pg, uid, headers, client = account
    result = client.get("/api/v1/me", headers=headers)
    assert result.status_code == 200
    assert result.headers["cache-control"] == "no-store"
    assert result.headers["etag"] == '"0"'
    assert result.json() == {
        "user_id": str(uid),
        "display_name": None,
        "preferred_locale": "en",
        "email_verified": True,
        "masked_contact": {"phone": None},
        "version": "0",
    }
    with pg.connect() as c:
        assert (
            c.execute(
                text("SELECT count(*) FROM public.user_profiles WHERE user_id=:uid"),
                {"uid": uid},
            ).scalar_one()
            == 0
        )


def test_create_update_commit_and_stale_version_preserve_newer_profile(account):
    pg, uid, headers, client = account
    first = edit(
        client, headers, "0", {"display_name": "  علی 🙂  ", "preferred_locale": "ur"}
    )
    assert first.status_code == 200
    data = first.json()
    assert data["display_name"] == "علی 🙂" and data["preferred_locale"] == "ur"
    assert data["version"] != "0"
    assert edit(client, headers, "0", {"display_name": "stale"}).status_code == 412
    second = edit(client, headers, data["version"], {"display_name": "Updated"})
    assert second.status_code == 200
    assert second.json()["preferred_locale"] == "ur"
    assert second.json()["version"] != data["version"]
    with pg.connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT display_name FROM public.user_profiles WHERE user_id=:uid"
                ),
                {"uid": uid},
            ).scalar_one()
            == "Updated"
        )


@pytest.mark.parametrize(
    "body",
    [
        {"role": "superadmin"},
        {"owner_id": str(uuid.uuid4())},
        {"email_verified": True},
        {"preferred_locale": None},
        {"preferred_locale": "fr"},
        {},
        {"display_name": "\n"},
        {"display_name": 123},
        {"display_name": "x" * 121},
    ],
)
def test_invalid_or_privilege_fields_never_write_or_echo_input(account, body):
    pg, uid, headers, client = account
    result = edit(client, headers, "0", body)
    assert result.status_code == 400
    assert result.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "superadmin" not in result.text
    with pg.connect() as c:
        assert (
            c.execute(
                text("SELECT count(*) FROM public.user_profiles WHERE user_id=:uid"),
                {"uid": uid},
            ).scalar_one()
            == 0
        )


@pytest.mark.parametrize("initialized", [False, True])
def test_concurrent_profile_edits_commit_exactly_one_and_fence_stale_writer(
    account, initialized
):
    pg, uid, headers, client = account
    version = "0"
    if initialized:
        version = edit(client, headers, version, {"display_name": "Initial"}).json()[
            "version"
        ]
    barrier = Barrier(2)

    def update(name):
        barrier.wait(timeout=10)
        response = edit(client, headers, version, {"display_name": name})
        return response.status_code, name

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(update, ["Writer A", "Writer B"]))
    assert sorted(code for code, _ in results) == [200, 412]
    winner = next(name for code, name in results if code == 200)
    with pg.connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT display_name FROM public.user_profiles WHERE user_id=:uid"
                ),
                {"uid": uid},
            ).scalar_one()
            == winner
        )
        events = (
            c.execute(
                text(
                    "SELECT safe_details FROM public.audit_events WHERE target_id=:uid AND action='account.profile.update'"
                ),
                {"uid": uid},
            )
            .scalars()
            .all()
        )
        assert len(events) == (2 if initialized else 1)
        assert all(set(event) == {"version"} for event in events)


def test_audit_failure_rolls_back_profile_and_connection_recovers(account):
    pg, _uid, headers, client = account
    # Exact temporary fixture schema only; no installed/public trigger changes.
    with pg.connect() as c:
        c.execute(
            text(
                "CREATE FUNCTION public.sr22_fail_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'injected audit failure' USING ERRCODE='23514'; END $$"
            )
        )
        c.execute(
            text(
                "CREATE TRIGGER sr22_fail_audit BEFORE INSERT ON public.audit_events FOR EACH ROW EXECUTE FUNCTION public.sr22_fail_audit()"
            )
        )
        c.commit()
    try:
        result = edit(client, headers, "0", {"display_name": "must rollback"})
        assert result.status_code == 503 and "injected" not in result.text
        assert client.get("/api/v1/me", headers=headers).json()["version"] == "0"
    finally:
        with pg.connect() as c:
            c.execute(text("DROP TRIGGER sr22_fail_audit ON public.audit_events"))
            c.execute(text("DROP FUNCTION public.sr22_fail_audit()"))
            c.commit()
    assert edit(client, headers, "0", {"display_name": "Recovered"}).status_code == 200


def test_cross_user_body_cannot_mutate_another_account(account, guarded):  # noqa: F811
    _, uid, headers, client = account
    _, wf, _, _, other_headers, _ = guarded
    result = edit(client, headers, "0", {"display_name": "Own"})
    assert result.status_code == 200
    own = client.get("/api/v1/me", headers=headers).json()
    other = client.get("/api/v1/me", headers=other_headers(wf["b"])).json()
    assert other["user_id"] != str(uid)
    assert (
        edit(
            client, other_headers(wf["b"]), own["version"], {"display_name": "Attack"}
        ).status_code
        == 412
    )
    assert client.get("/api/v1/me", headers=headers).json() == own


def test_bad_body_content_type_version_and_missing_auth_fail_safely(account):
    _, _, headers, client = account
    assert client.get("/api/v1/me").status_code == 401
    assert (
        client.request(
            "PATCH", "/api/v1/me", headers=headers, json={"display_name": "Name"}
        ).status_code
        == 400
    )
    assert (
        client.request(
            "PATCH",
            "/api/v1/me",
            headers={**headers, "If-Match": '"0"'},
            content="not-json",
        ).status_code
        == 415
    )
    result = client.request(
        "PATCH",
        "/api/v1/me",
        headers={**headers, "If-Match": '"0"', "Content-Type": "application/json"},
        content='{"token":"synthetic-private-token"',
    )
    assert result.status_code == 400 and "synthetic-private-token" not in result.text
