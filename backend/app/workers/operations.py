"""Offline operational policy model. No CLI, clock, database or provider adapter.

Ownership and lease objects model decisions only; they provide no distributed
lock or production authorization. All observation output is synthetic.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite


class Job(StrEnum):
    NOTIFICATIONS = "notifications"
    PRINTING = "printing"
    FINANCE = "finance-sync"


class State(StrEnum):
    DISABLED = "disabled"
    NOT_OBSERVED = "not_observed"
    POLLING = "polling"
    IDLE = "idle"
    WORKING = "working"
    DRAINING = "draining"
    STOPPED = "stopped"
    ERROR = "error"


class Refused(ValueError):
    """Fixed category only; never include raw configuration or payloads."""


def number(value: object) -> float:
    if type(value) not in (int, float):
        raise Refused("invalid_number")
    try:
        converted = float(value)
    except OverflowError:
        raise Refused("invalid_number") from None
    if not isfinite(converted) or converted < 0:
        raise Refused("invalid_number")
    return converted


def digest(value: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise Refused("invalid_release")
    if any(c not in "0123456789abcdef" for c in value):
        raise Refused("invalid_release")
    return value


@dataclass(frozen=True)
class Compatibility:
    """Exact reviewed release/schema/payload pairs, not ordered version guesses."""

    release_digest: str
    schema_revision: str
    payload_versions: frozenset[int]

    def __post_init__(self):
        digest(self.release_digest)
        if (
            not isinstance(self.schema_revision, str)
            or not self.schema_revision
            or type(self.payload_versions) is not frozenset
            or not self.payload_versions
        ):
            raise Refused("compatibility_unreviewed")
        if any(type(v) is not int or v < 1 for v in self.payload_versions):
            raise Refused("compatibility_unreviewed")

    def admits(self, release: str, schema: str, payload: int) -> bool:
        return (
            release == self.release_digest
            and schema == self.schema_revision
            and type(payload) is int
            and payload in self.payload_versions
        )


@dataclass(frozen=True)
class Lease:
    owner: str
    attempt: int
    expires_at: float

    def __post_init__(self):
        if (
            not isinstance(self.owner, str)
            or not self.owner
            or type(self.attempt) is not int
            or self.attempt < 1
        ):
            raise Refused("invalid_lease")
        number(self.expires_at)

    def permits(self, current: "Lease", now: float) -> bool:
        return self == current and number(now) < self.expires_at


@dataclass
class Ownership:
    """In-memory singleton model; intentionally no platform enforcement claim."""

    owners: dict[Job, str] = field(default_factory=dict)

    def acquire(self, job: Job, owner: str) -> None:
        if (
            not isinstance(job, Job)
            or not isinstance(owner, str)
            or not owner
            or job in self.owners
        ):
            raise Refused("duplicate_or_invalid_owner")
        self.owners[job] = owner

    def release(self, job: Job, owner: str) -> None:
        if self.owners.get(job) != owner:
            raise Refused("owner_mismatch")
        del self.owners[job]


@dataclass
class Supervisor:
    job: Job
    release_digest: str
    enabled: bool = False
    state: State = field(init=False)
    active: Lease | None = field(default=None, init=False)
    last_poll_at: float | None = field(default=None, init=False)
    last_completion_at: float | None = field(default=None, init=False)
    last_started_at: float | None = field(default=None, init=False)
    error_code: str | None = field(default=None, init=False)
    last_time: float = field(default=0, init=False)
    stopping: bool = field(default=False, init=False)

    def __post_init__(self):
        if not isinstance(self.job, Job) or type(self.enabled) is not bool:
            raise Refused("invalid_policy")
        digest(self.release_digest)
        self.state = State.NOT_OBSERVED if self.enabled else State.DISABLED

    def _time(self, now: float) -> float:
        value = number(now)
        if value < self.last_time:
            raise Refused("clock_regressed")
        self.last_time = value
        return value

    def begin_poll(self, now: float) -> None:
        value = self._time(now)
        if self.stopping or self.state not in (
            State.NOT_OBSERVED,
            State.IDLE,
            State.ERROR,
        ):
            raise Refused("admission_closed")
        if self.last_started_at is not None and value - self.last_started_at < 5:
            raise Refused("poll_not_due")
        self.last_started_at = value
        self.state = State.POLLING
        self.error_code = None

    def poll_result(self, now: float, lease: Lease | None, *, ok: bool) -> None:
        value = self._time(now)
        if self.state != State.POLLING or type(ok) is not bool:
            raise Refused("poll_not_active")
        if not ok:
            if lease is not None:
                raise Refused("failed_poll_with_claim")
            self.state, self.error_code = State.ERROR, "poll_unavailable"
            if self.stopping:
                self.state = State.STOPPED
            return
        if lease is not None and not lease.permits(lease, value):
            raise Refused("expired_claim")
        self.last_poll_at = value
        self.active = lease
        self.state = State.WORKING if lease else State.IDLE
        if self.stopping:
            self.state = State.DRAINING if lease else State.STOPPED

    def stop_admission(self) -> None:
        self.stopping = True
        if self.state in (State.DISABLED, State.STOPPED):
            return
        # A poll already admitted may return a claim; wait for its result.
        if self.state == State.POLLING:
            return
        self.state = State.DRAINING if self.active else State.STOPPED

    def finish(self, current: Lease, now: float, *, success: bool) -> bool:
        value = self._time(now)
        if self.active is None or self.state not in (State.WORKING, State.DRAINING):
            raise Refused("no_active_iteration")
        if type(success) is not bool:
            raise Refused("invalid_result")
        authorized = self.active.permits(current, value)
        if authorized and success:
            self.last_completion_at = value
        self.error_code = None if authorized and success else "iteration_unconfirmed"
        self.active = None
        self.state = State.STOPPED if self.state == State.DRAINING else State.ERROR
        if authorized and success and self.state != State.STOPPED:
            self.state = State.NOT_OBSERVED
        return authorized and success

    def force_stop(self) -> None:
        """Forget local execution only; never releases/mutates a durable lease."""
        self.active = None
        self.stopping = True
        self.state = State.STOPPED
        self.error_code = "completion_unknown"

    def report(self, now: float) -> dict:
        value = self._time(now)
        return {
            "schema_version": 1,
            "job_kind": self.job.value,
            "release_digest": self.release_digest,
            "observed_at_utc": value,
            "execution_state": self.state.value,
            "last_poll_at": self.last_poll_at,
            "last_completion_at": self.last_completion_at,
            "active_count": int(self.active is not None),
            "pending_count": None,
            "retry_count": None,
            "dead_count": None,
            "expired_lease_count": None,
            "oldest_due_age_seconds": None,
            "observation_source": "synthetic_model",
            "error_code": self.error_code,
        }


def oldest_due_age(now: float, due_times: tuple[float, ...] | None) -> float | None:
    """Fixture aggregate only: None=unknown, empty successful read=0."""
    value = number(now)
    if due_times is None:
        return None
    times = tuple(number(t) for t in due_times)
    eligible = [t for t in times if t <= value]
    return value - min(eligible) if eligible else 0.0
