# Task6.3A — approved offline operational preparation

The owner approved A–C in output/task63a/CONTRACT_REVIEW.md. This is partial
backend preparation, not a deployed worker/scheduler or operational acceptance.
backend/app/workers/operations.py contains pure fixture-driven models only;
it has no main/daemon, DB/provider adapter, real clock, signal handler or writer.
The proposed TOML is deliberately not a Railway deployment configuration.

The approved design is one scheduling supervisor per job service, one replica,
one admitted iteration, five-second minimum between poll starts, no secondary
cron/API scheduler and no unbounded local queue. In-memory ownership refusal
does not enforce a singleton across processes or deployments. Independent
job services model separation; no measured queue fairness guarantee follows.
Disabled is default. Enabling an in-memory fixture is not feature activation.

Existing commands (source evidence only; NOT authorized to execute): from backend,
`python -m app.workers.notifications --once`,
`python -m app.workers.printing --once`,
`python -m app.workers.finance_retention --mode sync`.
Proposed future `python -m app.workers.operations --job notifications --poll-seconds 5`
(and printing/finance-sync equivalents) is NOT IMPLEMENTED. Running the module
does not poll or claim. No cleanup/all/retention/export/preview scheduling allowed.
No secret/environment loading or API/admin database fallback is supplied.

Stop admission models SIGTERM/SIGINT, including an already admitted pending poll:
the poll result may establish one claim to drain; no subsequent poll is allowed.
An admitted iteration may finish only with its exact unchanged owner/attempt/
expiry lease and before expiry. Forced stop changes local modeled state only;
it never clears a durable lease, resets attempts or claims completion. Completion
after forced stop or under a reclaimed/expired lease is rejected. Production
signal integration/resource close, measured DB/render/provider time bounds,
grace period and real process kill/reclaim behavior remain acceptance gates.

Existing SQL claim/fence/retry algorithms and idempotency rules are unchanged.
The supervisor adds no automatic retry/replay. At-least-once external work may
duplicate after lost acknowledgment. Exit0 of existing one-shot commands is
not sufficient job success evidence. No lease renewal is introduced.

Compatibility fixtures admit only exact reviewed release digest, schema revision
and explicitly supported payload versions. They do not inspect a real image,
database or frozen payload. Activation needs an immutable image/schema/payload/
renderer/assets/keys matrix, approved Linux/native/font isolation and measurements,
old admission stopped and incompatible overlap excluded. Retain compatible old
readers/assets/keys; unknown versions fail closed. Never migrate at startup.
Rollback disables admission while retaining jobs, attempts, leases, holds,
artifacts, audit/history and compatible readers; never destructive downgrade,
automatic hold release, blind replay or legacy-only fallback.

Reports are closed synthetic DTOs. UTC timestamps are supplied fixture epoch
seconds, not a sampled runtime clock. Process heartbeat, successful poll,
completion and provider acknowledgment are distinct; this model supplies only
synthetic state/poll/completion. Queue fields stay null because there is no DB
observation. A separate pure due-age function distinguishes unknown, successful
empty/future-only selection and oldest eligible due age. No private lease owner
or payload enters output. No current healthy/deployed/provider badge is produced.
No API status contract, frontend integration, collector or persistent heartbeat
writer is added. Operator/collector/access/retention/recipient/channel/escalation,
cadence/freshness/lag/dead-letter thresholds and platform grace remain unapproved.
No alert delivery/replay/payment/cleanup authority is inferred.

Reproduce ONLY synthetic evidence from repository root:

```powershell
backend/.venv/Scripts/python.exe -B ops/run-task63a-backend.py
```

The fixed one-file allowlist runs in a sanitized child using existing6.1A early
network/DNS/listener/process/SQLAlchemy engine guards, no dotenv/plugin autoload,
180s timeout,1MiB log cap, strict JUnit/collection/outcome reconciliation and
source/Git preservation. Parent process starts a test interpreter only, never
a worker; model tests never create another child. Python guards are not an OS
sandbox. No real SIGTERM/kill/DB/provider/container experiment is authorized.

Keep all existing acceptance gates, particularly6.1A PG/hosted/integration,
6.2A BLOCKED performance,4.4D legal/native/operational/frontend,4.4B inactive
intake,5.1B inactive publication, retention and other disabled jobs/features.
Installed0021/pending0022–0035 remain unchanged. No schema work is necessary.
Provisioning/staging/database execution needs a separately reviewed concrete
plan and explicit authorization. VERIFIED requires actual authorized deployment,
recovery, monitoring/routed alerts and accountable operational acceptance.
