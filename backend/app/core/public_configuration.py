"""Closed public metadata only; empty records confer no publication authority."""

from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Locale = Literal["en", "ur"]
Version = Annotated[str, Field(pattern=r"^[A-Za-z0-9._:-]{1,80}$")]


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class PublicLink(Closed):
    url: str = Field(max_length=2048)

    @field_validator("url")
    @classmethod
    def secure_url(cls, value):
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or "?" in value
            or "#" in value
            or any(c.isspace() or ord(c) < 32 for c in value)
            or "\\" in value
        ):
            raise ValueError("Invalid public URL")
        # Validate malformed ports as well, without exposing the input.
        _ = parsed.port
        return value


class ReviewedLink(PublicLink):
    approved: bool


class ReviewedPolicy(Closed):
    version: Version
    approved: bool
    en: ReviewedLink | None
    ur: ReviewedLink | None


class ReviewedMetadata(Closed):
    privacy: ReviewedPolicy | None
    terms: ReviewedPolicy | None
    support: ReviewedLink | None


# No legal/native-language approval, support contact or active policy is seeded.
REVIEWED_METADATA = ReviewedMetadata(privacy=None, terms=None, support=None)


class PolicyMetadata(Closed):
    status: Literal["available", "unavailable"]
    version: Version | None
    url: str | None
    locale: Locale | None

    @model_validator(mode="after")
    def consistent(self):
        values = (self.version, self.url, self.locale)
        if self.status == "available":
            if any(v is None for v in values):
                raise ValueError("Incomplete policy")
            PublicLink(url=self.url)
        elif any(v is not None for v in values):
            raise ValueError("Unavailable policy must be empty")
        return self


class Policies(Closed):
    privacy: PolicyMetadata
    terms: PolicyMetadata


class SupportMetadata(Closed):
    status: Literal["available", "unavailable"]
    url: str | None

    @model_validator(mode="after")
    def consistent(self):
        if (self.status == "available") != (self.url is not None):
            raise ValueError("Inconsistent support")
        if self.url is not None:
            PublicLink(url=self.url)
        return self


class ConfigurationFeatures(Closed):
    abuse_reporting_available: Literal[False]
    template_publication_available: Literal[False]


class ConsentVersions(Closed):
    finder_contact: tuple[Literal["finder-v1"], Literal["finder-public-v1"]]
    finder_location: tuple[Literal["location-v1"], Literal["finder-location-v1"]]
    ice_publication: tuple[Literal["ice-public-v1"]]
    ice_contact: tuple[Literal["ice-contact-v1"]]
    whatsapp_publication: tuple[Literal["wa-public-v1"]]
    abuse_report: tuple[Literal["abuse-report-v1"]]


class PublicConfiguration(Closed):
    supported_locales: tuple[Literal["en"], Literal["ur"]]
    default_locale: Literal["en"]
    locale: Locale
    public_features: ConfigurationFeatures
    max_finder_message_length: Literal[1000]
    privacy_policy_version: Version | None
    policies: Policies
    consent_versions: ConsentVersions
    support: SupportMetadata
    policy_publication_ready: bool

    @model_validator(mode="after")
    def consistent(self):
        ready = all(
            item.status == "available"
            for item in (self.policies.privacy, self.policies.terms, self.support)
        )
        if (
            self.privacy_policy_version != self.policies.privacy.version
            or self.policy_publication_ready != ready
        ):
            raise ValueError("Inconsistent public metadata")
        return self


class ErrorDetails(Closed):
    pass


class Error(Closed):
    code: Literal["PROVIDER_UNAVAILABLE", "VALIDATION_ERROR"]
    message: Literal["Service temporarily unavailable.", "Invalid request."]
    details: ErrorDetails


class ErrorResponse(Closed):
    error: Error


def select_policy(record: ReviewedPolicy | None, locale: Locale) -> PolicyMetadata:
    if record is not None and record.approved:
        for candidate in dict.fromkeys((locale, "en")):
            link = getattr(record, candidate)
            if link is not None and link.approved:
                return PolicyMetadata(
                    status="available",
                    version=record.version,
                    url=link.url,
                    locale=candidate,
                )
    return PolicyMetadata(status="unavailable", version=None, url=None, locale=None)


def configuration(metadata: ReviewedMetadata, locale: Locale) -> PublicConfiguration:
    # Revalidate even typed records: unsafe model_construct/copy is not authority.
    reviewed = ReviewedMetadata.model_validate(metadata.model_dump(warnings=False))
    privacy = select_policy(reviewed.privacy, locale)
    terms = select_policy(reviewed.terms, locale)
    link = reviewed.support
    support = SupportMetadata(
        status="available" if link and link.approved else "unavailable",
        url=link.url if link and link.approved else None,
    )
    return PublicConfiguration(
        supported_locales=("en", "ur"),
        default_locale="en",
        locale=locale,
        public_features=ConfigurationFeatures(
            abuse_reporting_available=False,
            template_publication_available=False,
        ),
        max_finder_message_length=1000,
        privacy_policy_version=privacy.version,
        policies=Policies(privacy=privacy, terms=terms),
        consent_versions=ConsentVersions(
            finder_contact=("finder-v1", "finder-public-v1"),
            finder_location=("location-v1", "finder-location-v1"),
            ice_publication=("ice-public-v1",),
            ice_contact=("ice-contact-v1",),
            whatsapp_publication=("wa-public-v1",),
            abuse_report=("abuse-report-v1",),
        ),
        support=support,
        policy_publication_ready=all(
            x.status == "available" for x in (privacy, terms, support)
        ),
    )
