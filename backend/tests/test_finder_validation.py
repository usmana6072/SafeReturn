import math

import pytest
from pydantic import ValidationError

from app.api.v1.public_actions import FinderMessageRequest


def payload(**changes):
    return {
        "finder_email": "finder@example.test",
        "message": "I found your keys.",
        "contact_consent_accepted": True,
        "consent_version": "finder-public-v1",
        **changes,
    }


def test_location_is_optional():
    assert FinderMessageRequest(**payload()).location is None


@pytest.mark.parametrize(
    "changes",
    [
        {"contact_consent_accepted": False},
        {"finder_email": None},
        {"preferred_contact": "phone"},
        {"message": " " * 20},
        {"message": "Found it"},
        {"finder_phone": "+1\u0662\u0663\u0664\u0665\u0666\u0667\u0668"},
        {"location": {"latitude": 1.0, "longitude": 2.0}},
        {
            "location": {"latitude": math.nan, "longitude": 2.0},
            "location_consent": True,
        },
        {
            "location": {"latitude": 1.0, "longitude": 2.0, "accuracy_m": math.inf},
            "location_consent": True,
        },
        {"location": {"latitude": 91.0, "longitude": 2.0}, "location_consent": True},
    ],
)
def test_rejects_invalid_contact_consent_message_and_coordinates(changes):
    with pytest.raises(ValidationError):
        FinderMessageRequest(**payload(**changes))


def test_accepts_consented_zero_coordinates():
    body = FinderMessageRequest(
        **payload(location={"latitude": 0.0, "longitude": 0.0}, location_consent=True)
    )
    assert body.location.latitude == 0


def test_accepts_documented_consent_fields():
    data = payload()
    del data["consent_version"]
    data["contact_consent_version"] = "finder-v1"
    data["location"] = {
        "latitude": 0.0,
        "longitude": 0.0,
        "consent_accepted": True,
        "consent_version": "location-v1",
    }
    assert FinderMessageRequest(**data).location.consent_accepted is True
