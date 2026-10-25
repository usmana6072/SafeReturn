"""Approved offline measurements only; no production SLO or capacity inference."""

import asyncio
import copy
import json
import math
import platform
import sys
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

CASES = (
    "config_asgi_empty",
    "qr_asgi_synthetic_projection",
    "jwt_warm_verification",
    "checkout_dto_validation",
    "finance_page_validation",
)
CONCURRENCY = (1, 4)
REPETITIONS = 3
WARMUP = 20
SAMPLES = 200
ALLOCATION_OPS = 20
ALLOCATION_LIMIT = 128 * 1024 * 1024
ACCEPTANCE = "blocked_missing_approved_budgets_and_representative_environment"
NOT_RUN = [
    "PostgreSQL_query_plans_locks_connections",
    "provider_latency",
    "deployed_API_capacity",
    "worker_backlogs_throughput",
    "cold_JWK_refresh",
    "frontend",
    "hosted_Linux_acceptance",
    "RSS_native_memory",
    "representative_pilot_arrival_rates",
    "signed_SLO_acceptance",
]
LIMITATIONS = [
    "synthetic_closed_loop_single_process",
    "memory_only_event_loop",
    "scripted_QR_database_not_SQL",
    "checkout_and_finance_DTOs_not_business_queries",
    "GIL_and_thread_scheduling",
    "setup_and_warmup_excluded_harness_overhead_included",
    "allocation_pass_instrumented_separately",
    "no_OS_memory_limit_or_sandbox_claim",
]


class InvalidMeasurement(ValueError):
    """Fixed category only; never capture raw operation exceptions/payloads."""


def nearest_rank(values, percentile):
    if not values or not 0 < percentile <= 1:
        raise InvalidMeasurement("invalid_quantile")
    if any(
        type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in values
    ):
        raise InvalidMeasurement("invalid_duration")
    return sorted(values)[math.ceil(percentile * len(values)) - 1]


def check_allocation(peak):
    if type(peak) is not int or not 0 <= peak <= ALLOCATION_LIMIT:
        raise InvalidMeasurement("allocation_stop")


def cell_result(case, concurrency, repetition, samples, wall_ns, cpu_ns):
    if len(samples) != SAMPLES or {s["index"] for s in samples} != set(range(SAMPLES)):
        raise InvalidMeasurement("incomplete_samples")
    succeeded = sum(s["outcome"] == "succeeded" for s in samples)
    if succeeded != SAMPLES:
        raise InvalidMeasurement("operation_failed")
    values = [s["duration_ns"] / 1_000_000 for s in samples]
    if wall_ns <= 0 or cpu_ns < 0:
        raise InvalidMeasurement("invalid_clock")
    return {
        "case_id": case,
        "concurrency": concurrency,
        "repetition": repetition,
        "attempted": SAMPLES,
        "succeeded": succeeded,
        "failed": SAMPLES - succeeded,
        "wall_seconds": wall_ns / 1e9,
        "cpu_seconds": cpu_ns / 1e9,
        "p50_ms": nearest_rank(values, 0.50),
        "p95_ms": nearest_rank(values, 0.95),
        "p99_ms": nearest_rank(values, 0.99),
        "min_ms": min(values),
        "max_ms": max(values),
        "throughput_success_per_second": succeeded / (wall_ns / 1e9),
        "response_bytes": sum(s["response_bytes"] for s in samples),
        "expected_status_count": SAMPLES if case in CASES[:2] else 0,
    }


class ScriptedQR:
    """Fixed synthetic interface: no SQL execution, counters, budgets or contention."""

    def __init__(self):
        self.tokens = tuple(f"synthetic62a{i:020d}" for i in range(32))
        self.records = {
            token: {
                "tag_type": "lost",
                "status": "active",
                "locale_options": ["en", "ur"],
                "lost_item": {
                    "label": f"Synthetic item {i}",
                    "description": "Synthetic fixture",
                    "reward_text": None,
                },
                "features": {
                    "finder_form_enabled": False,
                    "whatsapp_contact_enabled": False,
                    "location_sharing_available": False,
                },
            }
            for i, token in enumerate(self.tokens)
        }

    @contextmanager
    def transaction(self):
        yield self

    def execute(self, statement, params=None):
        name = str(statement)
        if "sr_public_scan_rate" in name:
            value = True
        elif "sr_public_qr_projection" in name:
            value = copy.deepcopy(self.records[params["token"]])
        elif name.startswith("SET LOCAL ROLE") or "set_config(" in name:
            value = None
        else:
            raise InvalidMeasurement("unexpected_scripted_operation")

        class Result:
            def scalar_one(self):
                return value

        return Result()


class Workloads:
    def __init__(self):
        # Guards are installed by child bootstrap before importing app/fixtures.
        import httpx
        import jwt
        from app.api.v1.checkout import QuoteRequest
        from app.api.v1.finance_reconciliation import Page
        from app.core.auth import JWTVerifier
        from app.core.config import Settings
        from app.main import create_app
        from cryptography.hazmat.primitives.asymmetric import ec

        self.quote_model, self.finance_model = QuoteRequest, Page
        self.db = ScriptedQR()
        self.app = create_app(Settings())
        self.app.state.database = self.db
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app),
            base_url="https://synthetic.invalid",
            trust_env=False,
        )
        self.quote = {
            "lines": [
                {
                    "variant_id": str(UUID(int=i + 1)),
                    "quantity": copies,
                    "qr_uses": [
                        {
                            "mode": "new_pair",
                            "tag_type": tag,
                            "copies": copies,
                            "client_pair_group": "synthetic-pair",
                        }
                    ],
                }
                for i, (tag, copies) in enumerate((("lost", 3), ("ice", 2)))
            ],
            "address": {
                "recipient_name": "Synthetic Person",
                "phone": "+12025550100",
                "address": "Synthetic fixture address",
                "city": "Synthetic City",
            },
            "contact_phone_confirmation": True,
        }
        timestamp = datetime(2026, 1, 1, tzinfo=UTC).isoformat()
        self.finance = tuple(
            {
                "order_id": str(UUID(int=i + 1)),
                "attempt_id": None,
                "reason_code": "REVIEW_PENDING",
                "observed_since": timestamp,
                "attempt_amount": None,
                "order_amount": "100.00",
                "currency": None,
                "order_currency": "PKR",
                "next_action": "review_payment",
            }
            for i in range(1000)
        )
        self.pages = tuple(
            {
                "as_of": timestamp,
                "items": list(self.finance[i : i + 100]),
                "next_cursor": None,
                "unavailable_checks": [
                    "BANK_LEDGER_AMOUNT_COMPARISON",
                    "REJECTED_REFERENCE_MATCHES",
                ],
            }
            for i in range(0, 1000, 100)
        )
        private = ec.generate_private_key(ec.SECP256R1())
        jwk = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(private.public_key()))
        jwk.update(kid="synthetic", alg="ES256", use="sig", key_ops=["verify"])
        self.jwk_calls = 0

        def mock(request):
            self.jwk_calls += 1
            return httpx.Response(200, json={"keys": [jwk]})

        self.verifier = JWTVerifier(
            Settings(
                supabase_url="https://synthetic.invalid", auth_jwks_cache_seconds=600
            ),
            transport=httpx.MockTransport(mock),
        )
        self.expiry = int(time.time()) + 1800
        self.tokens = tuple(
            jwt.encode(
                {
                    "iss": "https://synthetic.invalid/auth/v1",
                    "aud": "authenticated",
                    "sub": str(UUID(int=i + 1)),
                    "session_id": str(UUID(int=i + 100)),
                    "role": "authenticated",
                    "aal": "aal1",
                    "is_anonymous": False,
                    "iat": int(time.time()) - 1,
                    "exp": self.expiry,
                },
                private,
                algorithm="ES256",
                headers={"kid": "synthetic"},
            )
            for i in range(32)
        )
        self.verifier.verify(self.tokens[0])

    def prepare(self):
        if self.jwk_calls != 1 or time.time() >= self.expiry - 180:
            raise InvalidMeasurement("jwt_cache_contamination")
        if self.verifier.clock() - self.verifier.loaded_at >= self.verifier.ttl - 180:
            raise InvalidMeasurement("jwt_cache_contamination")

    def sync_operation(self, case, index):
        if case == "jwt_warm_verification":
            result = self.verifier.verify(self.tokens[index % 32])
            if result.user_id != UUID(int=index % 32 + 1):
                raise InvalidMeasurement("jwt_identity")
        elif case == "checkout_dto_validation":
            result = self.quote_model.model_validate(self.quote)
            if len(result.lines) != 2:
                raise InvalidMeasurement("checkout_shape")
        elif case == "finance_page_validation":
            result = self.finance_model.model_validate(self.pages[index % 10])
            if len(result.items) != 100:
                raise InvalidMeasurement("finance_shape")
        else:
            raise InvalidMeasurement("unknown_workload")
        return 0

    async def http_operation(self, case, index):
        from app.api.v1.public_qr import PublicQRProfile
        from app.core.public_configuration import PublicConfiguration

        if case == "config_asgi_empty":
            response = await self.client.get(
                "/api/v1/public/config",
                params={"lang": "en" if index % 2 == 0 else "ur"},
            )
            body = PublicConfiguration.model_validate_json(response.content)
            if (
                body.policy_publication_ready
                or body.public_features.abuse_reporting_available
                or body.public_features.template_publication_available
            ):
                raise InvalidMeasurement("config_authority")
        elif case == "qr_asgi_synthetic_projection":
            response = await self.client.get(
                "/api/v1/public/qr/" + self.db.tokens[index % 32]
            )
            body = PublicQRProfile.model_validate_json(response.content)
            if (
                body.tag_type != "lost"
                or body.status != "active"
                or body.ice is not None
            ):
                raise InvalidMeasurement("qr_projection")
        else:
            raise InvalidMeasurement("unknown_workload")
        if response.status_code != 200:
            raise InvalidMeasurement("http_status")
        return len(response.content)

    async def close(self):
        await self.client.aclose()
        self.verifier.close()


async def batch(workloads, case, concurrency, count, *, measured, executor=None):
    """Closed-loop fixed workers; queueing/scheduling stays inside cell wall time."""
    if (
        case not in CASES
        or type(concurrency) is not int
        or concurrency not in CONCURRENCY
        or count != (SAMPLES if measured else WARMUP)
    ):
        raise InvalidMeasurement("unapproved_batch")
    results = []
    http = case in CASES[:2]
    loop = asyncio.get_running_loop()
    pool = None if http else executor or ThreadPoolExecutor(max_workers=concurrency)

    def operation(index):
        started = time.perf_counter_ns()
        try:
            size = workloads.sync_operation(case, index)
            outcome = "succeeded"
        except Exception:  # noqa: BLE001 -- all workload errors become fixed numeric failure outcomes
            size, outcome = 0, "failed"
        return {
            "index": index,
            "duration_ns": time.perf_counter_ns() - started,
            "outcome": outcome,
            "response_bytes": size,
        }

    async def worker(worker_index):
        for index in range(worker_index, count, concurrency):
            if http:
                started = time.perf_counter_ns()
                try:
                    size = await workloads.http_operation(case, index)
                    outcome = "succeeded"
                except Exception:  # noqa: BLE001 -- never reflect payload/transport exceptions
                    size, outcome = 0, "failed"
                sample = {
                    "index": index,
                    "duration_ns": time.perf_counter_ns() - started,
                    "outcome": outcome,
                    "response_bytes": size,
                }
            else:
                sample = await loop.run_in_executor(pool, operation, index)
            results.append(sample)

    # Executors are created before timing; initial thread startup is warmed up.
    wall, cpu = time.perf_counter_ns(), time.process_time_ns()
    try:
        await asyncio.gather(*(worker(i) for i in range(concurrency)))
    finally:
        if pool is not None and executor is None:
            pool.shutdown(wait=True)
    elapsed, consumed = time.perf_counter_ns() - wall, time.process_time_ns() - cpu
    if not measured and any(s["outcome"] != "succeeded" for s in results):
        raise InvalidMeasurement("warmup_failed")
    return results, elapsed, consumed


def validate_report(report, samples):
    expected = {
        (case, c, r) for case in CASES for c in CONCURRENCY for r in range(REPETITIONS)
    }
    if set(report) != {
        "cells",
        "allocation_observations",
        "clock_resolution_seconds",
        "started_at_utc",
        "guard_mode",
    }:
        raise InvalidMeasurement("report_keys")
    if len(report["cells"]) != len(expected) or len(samples) != len(expected) * SAMPLES:
        raise InvalidMeasurement("incomplete_report")
    observed = set()
    for cell in report["cells"]:
        if type(cell["concurrency"]) is not int or type(cell["repetition"]) is not int:
            raise InvalidMeasurement("cell_identity")
        identity = (cell["case_id"], cell["concurrency"], cell["repetition"])
        if identity not in expected or identity in observed:
            raise InvalidMeasurement("duplicate_cell")
        observed.add(identity)
        entries = [
            s
            for s in samples
            if (s["case_id"], s["concurrency"], s["repetition"]) == identity
        ]
        if any(
            set(s)
            != {
                "case_id",
                "concurrency",
                "repetition",
                "index",
                "duration_ns",
                "outcome",
                "response_bytes",
            }
            for s in entries
        ):
            raise InvalidMeasurement("sample_keys")
        for sample in entries:
            if (
                type(sample["duration_ns"]) is not int
                or sample["duration_ns"] <= 0
                or type(sample["response_bytes"]) is not int
                or sample["response_bytes"] < 0
                or type(sample["index"]) is not int
            ):
                raise InvalidMeasurement("sample_values")
        calculated = cell_result(
            *identity, entries, cell["wall_seconds"] * 1e9, cell["cpu_seconds"] * 1e9
        )
        if set(cell) != set(calculated):
            raise InvalidMeasurement("cell_keys")
        for key, value in calculated.items():
            original = cell[key]
            if type(value) is float:
                if (
                    type(original) not in (int, float)
                    or not math.isfinite(original)
                    or not math.isclose(original, value, rel_tol=1e-12)
                ):
                    raise InvalidMeasurement("cell_values")
            elif type(original) is not type(value) or original != value:
                raise InvalidMeasurement("cell_values")
    allocations = report["allocation_observations"]
    if len(allocations) != len(CASES) or {a["case_id"] for a in allocations} != set(
        CASES
    ):
        raise InvalidMeasurement("allocation_cardinality")
    for entry in allocations:
        if (
            set(entry) != {"case_id", "operations", "traced_peak_bytes"}
            or entry["operations"] != ALLOCATION_OPS
        ):
            raise InvalidMeasurement("allocation_keys")
        check_allocation(entry["traced_peak_bytes"])
    if (
        type(report["clock_resolution_seconds"]) not in (int, float)
        or not math.isfinite(report["clock_resolution_seconds"])
        or report["clock_resolution_seconds"] <= 0
    ):
        raise InvalidMeasurement("invalid_clock")
    if report["guard_mode"] != "memory_selector_no_network_database_process":
        raise InvalidMeasurement("guard_missing")
    timestamp = datetime.fromisoformat(report["started_at_utc"])
    if timestamp.tzinfo is None or timestamp.utcoffset().total_seconds() != 0:
        raise InvalidMeasurement("invalid_timestamp")


async def measure(directory):
    import anyio.to_thread

    anyio.to_thread.current_default_thread_limiter().total_tokens = 4
    workloads = Workloads()
    samples, cells, allocations = [], [], []
    started = datetime.now(UTC).isoformat()
    try:
        for case in CASES:
            for concurrency in CONCURRENCY:
                for repetition in range(REPETITIONS):
                    workloads.prepare()
                    pool = (
                        None
                        if case in CASES[:2]
                        else ThreadPoolExecutor(max_workers=concurrency)
                    )
                    try:
                        await batch(
                            workloads,
                            case,
                            concurrency,
                            WARMUP,
                            measured=False,
                            executor=pool,
                        )
                        entries, wall, cpu = await batch(
                            workloads,
                            case,
                            concurrency,
                            SAMPLES,
                            measured=True,
                            executor=pool,
                        )
                    finally:
                        if pool is not None:
                            pool.shutdown(wait=True)
                    workloads.prepare()
                    samples.extend(
                        {
                            "case_id": case,
                            "concurrency": concurrency,
                            "repetition": repetition,
                            **s,
                        }
                        for s in entries
                    )
                    cells.append(
                        cell_result(case, concurrency, repetition, entries, wall, cpu)
                    )
        for case in CASES:
            workloads.prepare()
            tracemalloc.start()
            try:
                await batch(workloads, case, 1, ALLOCATION_OPS, measured=False)
                _, peak = tracemalloc.get_traced_memory()
                check_allocation(peak)
            finally:
                tracemalloc.stop()
            allocations.append(
                {
                    "case_id": case,
                    "operations": ALLOCATION_OPS,
                    "traced_peak_bytes": peak,
                }
            )
    finally:
        await workloads.close()
    report = {
        "cells": cells,
        "allocation_observations": allocations,
        "clock_resolution_seconds": time.get_clock_info("perf_counter").resolution,
        "started_at_utc": started,
        "guard_mode": "memory_selector_no_network_database_process",
    }
    validate_report(report, samples)
    write_json(directory / "measurement.json", report)
    write_json(directory / "samples.json", samples)


def write_json(path, value):
    path.write_text(
        json.dumps(value, allow_nan=False, indent=2) + "\n", encoding="utf-8"
    )


def child(directory):
    import task61a_offline

    if not task61a_offline.INSTALLED:
        raise InvalidMeasurement("guard_missing")
    try:
        asyncio.run(measure(Path(directory)))
    except Exception:  # noqa: BLE001 -- child boundary records only fixed safe failure category
        write_json(
            Path(directory) / "measurement-failure.json",
            {"category": "invalid_or_failed_measurement"},
        )
        return 1
    return 0


def environment(revision, dirty, head):
    return {
        "os": platform.system(),
        "python": sys.version.split()[0],
        "app_revision": revision,
        "dirty": dirty,
        "guard_mode": "memory_selector_no_network_database_process",
        "migration_head_source_only": head,
    }
