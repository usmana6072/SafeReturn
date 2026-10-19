"""Owner collections and privacy using signed requests and real PostgreSQL RLS."""

import uuid

import pytest
from sqlalchemy import text
from test_profiles import profile as _profile

pytest_plugins = ["test_auth_guards"]
profile = _profile


def auth(profile, actor=None):
    # Reuse the fixture's signed request headers without bypassing API auth.
    return profile[4]("GET", "lost").request.headers if actor is None else actor


def test_all_owned_pairs_and_qrs_page_without_duplicates(profile):
    _, _, ids, client, _, _, _ = profile
    headers = auth(profile)
    seen_pairs, seen_qrs = [], []
    for path, field, expected, seen in (
        (
            "tag-pairs",
            "pair_id",
            {str(ids["pair"]), str(ids["other_pair"])},
            seen_pairs,
        ),
        (
            "qr",
            "qr_id",
            {str(ids[k]) for k in ("lost", "ice", "other_lost", "other_ice")},
            seen_qrs,
        ),
    ):
        cursor = None
        while True:
            result = client.get(
                f"/api/v1/me/{path}?limit=1" + (f"&cursor={cursor}" if cursor else ""),
                headers=headers,
            )
            assert result.status_code == 200, result.text
            assert result.headers["cache-control"] == "no-store"
            page = result.json()
            assert len(page["items"]) == 1
            seen.append(page["items"][0][field])
            cursor = page["next_cursor"]
            if cursor is None:
                break
        assert len(seen) == len(set(seen)) and set(seen) == expected


@pytest.mark.parametrize(
    "query", ["limit=0", "limit=101", "cursor=not-a-cursor", "status=invalid"]
)
def test_invalid_pagination_is_bounded(profile, query):
    result = profile[3].get(f"/api/v1/me/tag-pairs?{query}", headers=auth(profile))
    assert result.status_code in (400, 422)


def test_filters_pair_detail_and_no_medical_or_phone_in_collections(profile):
    _, _, ids, client, request, _, _ = profile
    request(
        "PUT",
        "ice",
        {"display_name": "ICE alias", "medical_notes": "PRIVATE synthetic medical"},
    )
    response = client.get(
        f"/api/v1/me/qr?pair_id={ids['pair']}&tag_type=ice&status=active",
        headers=auth(profile),
    )
    assert response.status_code == 200, response.text
    assert [t["qr_id"] for t in response.json()["items"]] == [str(ids["ice"])]
    pair = client.get(f"/api/v1/me/tag-pairs/{ids['pair']}", headers=auth(profile))
    assert pair.status_code == 200 and len(pair.json()["tags"]) == 2
    assert {t["tag_type"] for t in pair.json()["tags"]} == {"lost", "ice"}
    for body in (pair.text, response.text):
        assert "PRIVATE synthetic medical" not in body
        assert "medical_notes" not in body and "ciphertext" not in body
        assert "phone" not in body and "secret_verifier" not in body


def test_cross_owner_unknown_and_unauthenticated_detail_are_concealed(profile, guarded):
    _, wf, ids, client, _, _, _ = profile
    other_headers = guarded[4](wf["a"])
    for resource, identity in (("qr", ids["lost"]), ("tag-pairs", ids["pair"])):
        foreign = client.get(f"/api/v1/me/{resource}/{identity}", headers=other_headers)
        missing = client.get(
            f"/api/v1/me/{resource}/{uuid.uuid4()}", headers=other_headers
        )
        assert foreign.status_code == missing.status_code == 404
        assert client.get(f"/api/v1/me/{resource}/{identity}").status_code == 401
    assert (
        client.get(
            f"/api/v1/me/qr?pair_id={ids['pair']}", headers=other_headers
        ).json()["items"]
        == []
    )


def test_owner_detail_includes_only_safe_identity_and_own_product_refs(profile):
    _, _, ids, client, _, _, _ = profile
    data = client.get(f"/api/v1/me/qr/{ids['lost']}", headers=auth(profile))
    assert data.status_code == 200, data.text
    assert data.json()["physical_products"] == []
    assert data.json()["profile_version"] == 0
    assert data.json()["editor_url"] == f"/my-qr/{ids['lost']}"


def test_read_collections_never_create_profiles_or_audit(profile):
    pg, _, _, client, _, _, _ = profile
    with pg.connect() as c:
        before = [
            c.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            for table in ("lost_item_profiles", "ice_profiles", "audit_events")
        ]
    for path in ("tag-pairs", "qr"):
        assert (
            client.get(f"/api/v1/me/{path}", headers=auth(profile)).status_code == 200
        )
    with pg.connect() as c:
        after = [
            c.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            for table in ("lost_item_profiles", "ice_profiles", "audit_events")
        ]
    assert before == after


def test_search_and_publication_filters_are_owner_scoped(profile):
    _, _, ids, client, request, _, _ = profile
    request("PUT", "lost", {"item_label": "Searchable bag", "published": True})
    headers = auth(profile)
    result = client.get(
        "/api/v1/me/qr?search=SEARCHABLE&publication=published", headers=headers
    )
    assert result.status_code == 200, result.text
    assert [q["qr_id"] for q in result.json()["items"]] == [str(ids["lost"])]
    drafts = client.get("/api/v1/me/qr?publication=draft", headers=headers)
    assert len(drafts.json()["items"]) == 3
    assert (
        client.get("/api/v1/me/qr?search=%27%20OR%201=1--", headers=headers).json()[
            "items"
        ]
        == []
    )
