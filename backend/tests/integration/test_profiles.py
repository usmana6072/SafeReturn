"""Task 3.3 signed requests against real PostgreSQL, isolated from user data."""

import base64
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic import SecretStr
from sqlalchemy import text

from app.core.config import Settings

pytest_plugins = ["test_auth_guards"]


@pytest.fixture
def profile(guarded):
    pg, wf, _, sessions, headers, client = guarded
    uid, sid, batch = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    ids = {
        name: uuid.uuid4()
        for name in ("pair", "other_pair", "lost", "ice", "other_lost", "other_ice")
    }
    # All interpolated values are locally generated UUIDs, never input/env values.
    setup = f"""DO $$ BEGIN
      INSERT INTO auth.users(id,email_confirmed_at) VALUES('{uid}',now());
      INSERT INTO auth.sessions(id,user_id,aal,not_after) VALUES('{sid}','{uid}','aal2',now()+interval '1 hour');
      INSERT INTO public.qr_batches(id,batch_code,ecc_level) VALUES('{batch}','{batch.hex}','Q');
    """
    for pair_name, lost, ice in (
        ("pair", "lost", "ice"),
        ("other_pair", "other_lost", "other_ice"),
    ):
        pid = ids[pair_name]
        setup += f"INSERT INTO public.tag_pairs(id,pair_reference,batch_id,owner_user_id,ownership_status,activated_at) VALUES('{pid}','{pid.hex}','{batch}','{uid}','active',now());"
        for name, kind in ((lost, "lost"), (ice, "ice")):
            qid = ids[name]
            setup += f"INSERT INTO public.qr_codes(id,pair_id,tag_type,serial_number,public_token,ecc_level,public_status) VALUES('{qid}','{pid}','{kind}','{qid.hex}','{qid.hex}{uuid.uuid4().hex}','Q','active');"
    setup += " END $$;"
    with pg.connect() as c:
        c.execute(text(setup))
        c.commit()
    sessions[uid] = sid
    settings = Settings(
        profile_data_keys=SecretStr(
            json.dumps({"1": base64.urlsafe_b64encode(bytes([77]) * 32).decode()})
        )
    )
    client.application.state.settings = settings

    def request(
        method, kind, body=None, version=0, tag=None, recent=True, actor=None, suffix=""
    ):
        names = {
            "lost": "lost-profile",
            "ice": "ice-profile",
            "contacts": "ice-contacts",
            "preferences": "contact-preferences",
        }
        qid = ids[tag or ("ice" if kind in ("ice", "contacts") else "lost")]
        extra = {
            "amr": [
                {
                    "method": "password",
                    "timestamp": int(time.time()) - (1 if recent else 3600),
                }
            ]
        }
        auth_headers = headers(actor or uid, **extra)
        if method != "GET":
            auth_headers["If-Match"] = f'"{version}"'
        kwargs = {"headers": auth_headers}
        if body is not None:
            kwargs["json"] = body
        return client.request(
            method, f"/api/v1/me/qr/{qid}/{names[kind]}{suffix}", **kwargs
        )

    return pg, wf, ids, client, request, settings, uid


def consent(**extra):
    return {
        "published": True,
        "publication_consent_accepted": True,
        "publication_consent_version": "ice-public-v1",
        **extra,
    }


def contact(**extra):
    return {
        "relationship_label": "Parent",
        "phone": "+923001234567",
        "published": True,
        "publication_consent_accepted": True,
        "publication_consent_version": "ice-contact-v1",
        **extra,
    }


def test_missing_profiles_and_preferences_are_private_defaults_without_get_writes(
    profile,
):
    pg, _, ids, _, request, _, _ = profile
    for kind in ("lost", "ice", "contacts", "preferences"):
        response = request("GET", kind)
        assert response.status_code == 200, response.text
        assert response.json()["version"] == 0
        assert response.headers["etag"] == '"0"'
        assert response.headers["cache-control"] == "no-store"
    with pg.connect() as c:
        for table in ("lost_item_profiles", "ice_profiles", "tag_contact_preferences"):
            assert (
                c.execute(
                    text(f"SELECT count(*) FROM {table} WHERE qr_id IN (:lost,:ice)"),
                    ids,
                ).scalar_one()
                == 0
            )


def test_lost_edit_is_independent_and_stale_updates_do_not_audit(profile):
    pg, _, ids, _, request, _, _ = profile
    result = request(
        "PUT",
        "lost",
        {
            "item_label": "  بیگ  ",
            "description": "Synthetic description",
            "published": True,
        },
    )
    assert result.status_code == 200, result.text
    assert result.json()["item_label"] == "بیگ" and result.json()["version"] == 1
    assert request("PUT", "lost", {"item_label": "stale"}).status_code == 412
    assert request("GET", "lost", tag="other_lost").json()["version"] == 0
    assert request("GET", "ice").json()["version"] == 0
    assert request("GET", "preferences").json()["whatsapp_enabled"] is False
    assert request("PUT", "lost", {"item_label": None}, version=1).status_code == 400
    with pg.connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM audit_events WHERE target_id=:lost AND action='profile.lost.updated'"
                ),
                ids,
            ).scalar_one()
            == 1
        )


@pytest.mark.parametrize("kind", ["lost", "ice", "contacts", "preferences"])
def test_cross_owner_and_wrong_purpose_are_concealed(profile, kind):
    _, wf, _, _, request, _, _ = profile
    assert request("GET", kind, actor=wf["a"]).status_code == 404
    wrong = "lost" if kind in ("ice", "contacts") else "ice"
    assert request("GET", kind, tag=wrong).status_code == 404


def test_private_medical_notes_are_encrypted_owner_only_and_not_autopublished(profile):
    pg, wf, ids, _, request, _, _ = profile
    value = "Synthetic private medical note"
    result = request(
        "PUT", "ice", {"display_name": "Owner supplied", "medical_notes": value}
    )
    assert result.status_code == 200, result.text
    assert result.json()["medical_notes"] == value
    assert (
        result.json()["published"] is False
        and result.json()["show_medical_notes"] is False
    )
    assert request("GET", "ice", actor=wf["a"]).status_code == 404
    assert request("GET", "ice", tag="other_ice").json()["medical_notes"] is None
    with pg.connect() as c:
        ciphertext, version = c.execute(
            text(
                "SELECT medical_notes_ciphertext,medical_notes_key_version FROM ice_profiles WHERE qr_id=:ice"
            ),
            ids,
        ).one()
        assert value.encode() not in ciphertext and version == 1
        assert value not in str(
            c.execute(
                text("SELECT safe_details FROM audit_events WHERE target_id=:ice"), ids
            ).all()
        )


def test_ice_publication_requires_versioned_consent_and_recent_authentication(profile):
    _, _, _, _, request, _, _ = profile
    body = {
        "display_name": "Synthetic ICE",
        "medical_notes": "Synthetic note",
        "show_medical_notes": True,
        "published": True,
    }
    assert request("PUT", "ice", body).status_code == 422
    assert request("PUT", "ice", consent(**body), recent=False).status_code == 403
    result = request("PUT", "ice", consent(**body))
    assert result.status_code == 200, result.text
    assert result.json()["publication_consent_version"] == "ice-public-v1"
    assert (
        request("PUT", "ice", {"medical_notes": "Changed"}, version=1).status_code
        == 422
    )
    assert request("PUT", "ice", {"display_name": "Stale"}).status_code == 412
    assert (
        request("PUT", "ice", {"published": False}, version=1).json()[
            "show_medical_notes"
        ]
        is False
    )


def test_medical_unpublication_survives_missing_key_but_new_encryption_fails_closed(
    profile,
):
    pg, _, ids, client, request, _, _ = profile
    assert (
        request(
            "PUT",
            "ice",
            consent(medical_notes="Synthetic note", show_medical_notes=True),
        ).status_code
        == 200
    )
    client.application.state.settings = Settings(profile_data_keys=None)
    assert request("GET", "ice").status_code == 503
    result = request("PUT", "ice", {"published": False}, version=1)
    assert result.status_code == 200, result.text
    assert (
        result.json()["published"] is False
        and result.json()["medical_notes_redacted"] is True
    )
    assert (
        request("PUT", "ice", {"medical_notes": "New notes"}, version=2).status_code
        == 503
    )
    with pg.connect() as c:
        assert c.execute(
            text(
                "SELECT profile_version,published,medical_notes_ciphertext IS NOT NULL FROM ice_profiles WHERE qr_id=:ice"
            ),
            ids,
        ).one() == (2, False, True)


def test_contact_crud_is_masked_consented_versioned_and_soft_removed(profile):
    pg, _, ids, _, request, _, _ = profile
    result = request("POST", "contacts", contact())
    assert result.status_code == 201, result.text
    assert "+923001234567" not in result.text
    assert result.json()["phone_masked"].endswith("4567")
    cid = result.json()["contact_id"]
    assert (
        request(
            "PATCH", "contacts", {"phone": "+923009876543"}, version=1, suffix=f"/{cid}"
        ).status_code
        == 422
    )
    assert (
        request(
            "PATCH", "contacts", {"published": False}, tag="other_ice", suffix=f"/{cid}"
        ).status_code
        == 404
    )
    updated = request(
        "PATCH", "contacts", contact(phone="+923009876543"), version=1, suffix=f"/{cid}"
    )
    assert updated.status_code == 200, updated.text
    removed = request("DELETE", "contacts", version=2, suffix=f"/{cid}")
    assert removed.status_code == 204 and not removed.content
    assert request("GET", "contacts").json() == {"contacts": [], "version": 3}
    with pg.connect() as c:
        row = c.execute(
            text(
                "SELECT phone_ciphertext,published,removed_at IS NOT NULL,publication_consent_version FROM ice_contacts WHERE id=:id"
            ),
            {"id": cid},
        ).one()
        assert b"923009876543" not in row[0] and row[1:] == (
            False,
            True,
            "ice-contact-v1",
        )
        assert (
            c.execute(
                text("SELECT count(*) FROM lost_item_profiles WHERE qr_id=:lost"), ids
            ).scalar_one()
            == 0
        )


def test_contact_limit_and_stale_collection_version(profile):
    _, _, _, _, request, _, _ = profile
    for version in range(3):
        result = request("POST", "contacts", contact(published=False), version=version)
        assert result.status_code == 201, result.text
    assert (
        request("POST", "contacts", contact(published=False), version=3).status_code
        == 422
    )
    assert len(request("GET", "contacts").json()["contacts"]) == 3
    assert (
        request("PUT", "ice", {"display_name": "Stale profile"}, version=2).status_code
        == 412
    )


def test_contact_unpublication_and_removal_do_not_need_encryption_key(profile):
    _, _, _, client, request, _, _ = profile
    cid = request("POST", "contacts", contact()).json()["contact_id"]
    client.application.state.settings = Settings(profile_data_keys=None)
    result = request(
        "PATCH", "contacts", {"published": False}, version=1, suffix=f"/{cid}"
    )
    assert result.status_code == 200, result.text
    assert result.json()["published"] is False and result.json()["phone_masked"] is None
    assert request("DELETE", "contacts", version=2, suffix=f"/{cid}").status_code == 204


def test_whatsapp_has_independent_version_explicit_disclosure_and_outage_safe_disable(
    profile,
):
    pg, _, ids, client, request, _, _ = profile
    body = {"whatsapp_enabled": True, "whatsapp_phone": "+923001234567"}
    assert request("PUT", "preferences", body).status_code == 422
    body.update(public_disclosure_consent=True, consent_version="wa-public-v1")
    result = request("PUT", "preferences", body)
    assert result.status_code == 200, result.text
    assert "+923001234567" not in result.text
    assert request("GET", "lost").json()["version"] == 0
    assert (
        request("GET", "preferences", tag="other_lost").json()["whatsapp_enabled"]
        is False
    )
    client.application.state.settings = Settings(profile_data_keys=None)
    result = request("PUT", "preferences", {"whatsapp_enabled": False}, version=1)
    assert result.status_code == 200 and result.json()["whatsapp_phone_masked"] is None
    with pg.connect() as c:
        assert c.execute(
            text(
                "SELECT whatsapp_enabled,profile_version FROM tag_contact_preferences WHERE qr_id=:lost"
            ),
            ids,
        ).one() == (False, 2)


@pytest.mark.parametrize("resource", ["lost", "contacts"])
def test_concurrent_creates_have_one_winner_and_one_stale_version(profile, resource):
    _, _, _, _, request, _, _ = profile
    method, body = (
        ("PUT", {"item_label": "Winner"})
        if resource == "lost"
        else ("POST", contact(published=False))
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: request(method, resource, body), range(2)))
    assert sorted(result.status_code for result in results) == (
        [200, 412] if resource == "lost" else [201, 412]
    )


@pytest.mark.parametrize(
    "body",
    [
        {"owner_user_id": "private-input-never-echo"},
        {"description": "<script>private-input-never-echo</script>"},
        {"published": None},
        {"item_label": "x" * 121},
    ],
)
def test_validation_is_bounded_and_never_echoes_private_input(profile, body):
    _, _, _, _, request, _, _ = profile
    result = request("PUT", "lost", body)
    assert result.status_code == 400
    assert "private-input-never-echo" not in result.text


def test_audit_failure_rolls_back_profile_and_version_then_retry_succeeds(profile):
    pg, _, ids, _, request, _, _ = profile
    with pg.connect() as c:
        c.execute(
            text(
                "CREATE FUNCTION public.test_profile_audit_failure() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'injected profile audit failure' USING ERRCODE='23514'; END $$"
            )
        )
        c.execute(
            text(
                "CREATE TRIGGER test_profile_audit_failure BEFORE INSERT ON public.audit_events FOR EACH ROW WHEN (NEW.action='profile.lost.updated') EXECUTE FUNCTION public.test_profile_audit_failure()"
            )
        )
        c.commit()
    try:
        assert request("PUT", "lost", {"item_label": "Rollback"}).status_code == 503
        with pg.connect() as c:
            assert (
                c.execute(
                    text("SELECT count(*) FROM lost_item_profiles WHERE qr_id=:lost"),
                    ids,
                ).scalar_one()
                == 0
            )
    finally:
        with pg.connect() as c:
            c.execute(
                text("DROP TRIGGER test_profile_audit_failure ON public.audit_events")
            )
            c.execute(text("DROP FUNCTION public.test_profile_audit_failure()"))
            c.commit()
    assert request("PUT", "lost", {"item_label": "Retry"}).status_code == 200


def test_consent_audit_captures_states_and_accepted_versions_without_personal_values(
    profile,
):
    pg, _, ids, _, request, _, _ = profile
    assert (
        request(
            "PUT", "lost", {"item_label": "Synthetic label", "published": True}
        ).status_code
        == 200
    )
    assert (
        request("PUT", "ice", consent(display_name="Synthetic ICE")).status_code == 200
    )
    created = request("POST", "contacts", contact(), version=1)
    assert created.status_code == 201, created.text
    assert (
        request(
            "PUT",
            "preferences",
            {
                "whatsapp_enabled": True,
                "whatsapp_phone": "+923001234567",
                "public_disclosure_consent": True,
                "consent_version": "wa-public-v1",
            },
        ).status_code
        == 200
    )
    assert (
        request(
            "DELETE", "contacts", version=2, suffix="/" + created.json()["contact_id"]
        ).status_code
        == 204
    )
    with pg.connect() as c:
        events = c.execute(
            text(
                "SELECT action,safe_details FROM audit_events WHERE target_id IN (:lost,:ice) ORDER BY occurred_at"
            ),
            ids,
        ).all()
        assert len(events) == 5
        versions = set()
        for _, details in events:
            assert isinstance(details["version"], int)
            assert "from_status" in details and "to_status" in details
            assert "+923001234567" not in str(details) and "Synthetic" not in str(
                details
            )
            if "reason_code" in details:
                versions.add(details["reason_code"])
        assert versions == {"ice-public-v1", "ice-contact-v1", "wa-public-v1"}
