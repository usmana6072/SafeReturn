# Phase 9 migration 0044 deployment safety review

Date: 2026-10-24, Asia/Karachi. Decision: **NOT READY FOR EXECUTION** for the combined migration and command-login setup. No migration, role appointment, credential creation, account creation, grant, frontend enablement or Phase 10 work was executed.

Latest continuation: readiness inspection completed within the authorized scope. **No suitable isolated disposable managed-Auth database is configured; real migration/security/rollback/concurrency tests remain NOT EXECUTED.** The configured test URL identifies the protected development project, so it was rejected as a disposable target. Exact missing isolation/fixture approval, credential lifecycle requirements, executable recovery commands and prepared test assertions are now incorporated into the existing [operation runbook](../ops/SUPPORT_DEVELOPMENT_EXCEPTION.md#migration-0044-readiness-completion-review--2026-10-24). No new Phase 9 task/subdivision was created.

## Evidence and scope

Reviewed 0044 SQL/Python, 0043 and upstream RLS/account/session/Support migrations, BTR-01 development exception v1.1, the development command runbook, provisioning CLI/service and central route fence, and existing database/security/deployment specifications. The v1.1 exception governs this sole development case; it does not supersede unrelated security rules.

An exact-project, verify-full connection using the existing migration inspection credential executed a read-only transaction, then rolled back. No Auth identity/session/factor rows, business records, Storage records or QR records were read. Catalog column names are metadata, not secret values. Results: `tmp/phase9-step2/review-0044-catalog.json`; reusable read-only inspector: `tmp/phase9-step2/review_0044_catalog.py`. Initial runtime inspection was denied by existing ACLs; permissions were not changed.

Confirmed installed Alembic revision: **0043_standalone_activation**. Both proposed command roles and both exception tables are absent. Live Support SELECT policies include the existing retained-abuse restriction and assigned-only history predicate. Managed Auth exposes the columns used by 0044. These observations establish structural compatibility, not successful execution of the new PL/pgSQL functions.

Offline validation: **134 passed**, using `tests/test_support_development_provisioning.py`, `tests/test_staff_security.py`, and `tests/test_support_metadata.py`. This is not real PostgreSQL transaction/RLS/concurrency acceptance.

Those historical checks were **not rerun** during the readiness continuation. New executed checks were limited to the catalog/environment inspection, migration hashes, and the new recovery inspector's lint/default/read-only0043 path.

## Actual continuation evidence

`tmp/phase9-step2/inspect_0044_readiness.py` wrote `tmp/phase9-step2/readiness-0044-evidence.json` at 2026-10-24T07:00:29Z (12:00:29 Asia/Karachi). Initial sandbox socket failure was followed by an approved read-only retry. The successful transaction was explicitly READ ONLY and ended in ROLLBACK. No business/Auth/Storage/QR rows or QR command functions were accessed.

| Executed check | Actual result and limit |
|---|---|
| Server/revision | PostgreSQL170011 (17.11); sole revision0043_standalone_activation. |
| Restricted login/setup | Command/provisioner roles and memberships absent; command DSN unconfigured. No actual restricted-login test is possible yet; no credentials were created. |
| Existing RLS | Orders/products/staff/audit/Support/tag_pairs/qr_codes/Storage buckets+objects have RLS enabled. Existing Support abuse restriction and assigned-only history policies remain present. This metadata does not exercise row-level decisions. |
| Existing grants | No PUBLIC relation/column grants found in public/auth/storage. PUBLIC has public-schema USAGE and database CONNECT/TEMPORARY. Three sr_* PUBLIC EXECUTE entries are trigger helpers (sr_product_copy_price_required, sr_saved_address_guard, sr_saved_default_guard), not protected QR command entries. This is not proof of all-role/cross-schema effective privilege denial from a future login. |
| Ownership/defaults | Required installed helpers belong to postgres with pinned pg_catalog search_path; runtime API/worker roles are NOLOGIN, NOINHERIT, and lack elevated flags. Owner-specific default ACLs were recorded. Migration must run as the reviewed owner; creating its definers as the narrow provisioner would not work and is not permitted. |
| Disposable target discovery | The configured test target is remote and project-qualified to fhuxryfkfrvycsojkzvq. It was not used for tests. Portable PostgreSQL17.11 is available; Docker/Supabase CLI are absent from PATH, standard Docker installation path absent. Existing preserved55439 skeleton is not a managed-Auth test environment and was not connected/restarted/modified. No suitable isolated target found. |
| File hash check | Both0044 files exactly match the pinned hashes below; **no change since prior review**. Neither source was edited. |
| New recovery inspector | `backend/scripts/support_0044_recovery.py`: default pins-only mode PASSED without network; scoped Ruff PASSED; actual verify-full READ ONLY inspection returned0044_NOT_INSTALLED with no exception/receipt tables, provisioner/login or0044 fences. Post-installation/replay/revocation paths remain unexecuted. |
| Real PostgreSQL behavioral tests | **NOT EXECUTED**: migration commit/rollback/timeout, command-session ACL enforcement, command failure/replay, RLS/expiry/revoke and concurrent transactions require an isolated target and the fixture authority described below. No fabricated passing counts. |

PUBLIC capabilities cannot be subtracted by a REVOKE on just one login, and ordinary PostgreSQL role/catalog/type metadata is not generally private. The requirement means no ability to assume/modify unrelated roles, read/mutate unrelated application/Auth/Storage records or execute protected QR commands, not a claim that pg_roles/system catalogs are invisible. No shared PUBLIC grant was revoked. See [PostgreSQL privilege rules](https://www.postgresql.org/docs/17/ddl-priv.html).

## Eight requested checks

| Check | Finding |
|---|---|
| 0043 compatibility | Correct `down_revision`; freshly confirmed installed 0043 and required managed Auth columns. Real function execution remains untested. |
| Destructive operations | Migration has no DROP, TRUNCATE, data DELETE, existing-data UPDATE or backfill. UPDATE statements are inside the uninvoked command function and target only the eventual exact exception/grant revocation. No user, order, product, case, bucket or QR data mutation occurs during schema installation. |
| Minimum command privilege | Source creates a NOLOGIN restricted provisioner with public-schema USAGE and EXECUTE on only grant/revoke entry points. Runtime cannot invoke these or write exception tables. Login appointment is absent. Effective PUBLIC/inherited/transitive privileges, default ACLs, function ownership and appointment options still require verification; checking role flags and direct memberships alone does not prove minimum effective privilege. |
| Project and identity | CLI pins project fhuxryfkfrvycsojkzvq, endpoint, project-qualified login, CA, email usmana6072@gmail.com and configured UUID/owner manifest. SQL checks email but has no standalone project/approved-UUID binding; it relies on the trusted command host and configured connection for those controls. Actual dedicated UUID remains unbound, as account creation is excluded. Do not call the SQL directly as a substitute for CLI verification. |
| Lifetime and revoke | Immutable database expiry is at most created_at + 24 hours, also bounded by 2026-11-07T18:59:59Z (23:59:59 Asia/Karachi). This is conservative relative to commit + 24 hours. Database-clock read checks deny expired/revoked access, singleton consumption prevents regrant, and replay cannot extend expiry. Revoke can run after sunset with fresh authority/MFA. Real clock/locking/replay tests remain outstanding. |
| RLS/Auth/QR | Only restrictive Support SELECT fences are added; no existing policy/helper/Auth/QR handler is replaced. Existing assignment/abuse predicates remain necessary. No QR or Storage operation is present. Metadata-only scope also relies on the restarted, UUID-bound backend route fence; existing broader staff INSERT/UPDATE policies are not replaced. A disabled/stale backend is unsafe for any later grant. |
| Rollback/recovery | Migration uses Alembic's transaction and 3-second lock timeout; rollback on precommit failure is intended but not demonstrated for 0044 on PostgreSQL. Downgrade deliberately raises, retaining consumption/audit/receipt history. After commit use reviewed forward repair, not DROP/history deletion. Emergency revoke without available MFA/command credential and backup/receipt-key retention procedures are not yet concrete and verified. Never disable the backend fence while an exceptional grant could remain effective. |
| Exact operations | Candidate scope below is concrete for the migration and role capability. Credential appointment/transport and effective ACL verification are not finalized, so the combined operation cannot yet receive an execution-ready sign-off. |

## Exact candidate deployment scope — not executed

Pinned artifacts (SHA256 of exact current bytes):

- `backend/alembic/versions/0044_support_dev_exception.sql`: `17b3b5bd5964f6dfb7a1b610bce455d32fc805539282e3ecb7d79a9e39a19a2d`
- `backend/alembic/versions/0044_support_dev_exception.py`: `67318373a9fecdca0fa441697d37ae4a1c0719d7ce0dd1e125e85ea07ddc5c30`

For a later authorized deployment, use a dedicated runner with an explicitly injected, verified connection to only fhuxryfkfrvycsojkzvq. In the deployment transaction recheck that the sole installed revision is exactly 0043, verify artifact hashes and absence of conflicting objects, and invoke `alembic.command.upgrade(config, "0044_support_dev_exception")` with `config.attributes["connection"]` set to that connection. No `upgrade head`, stamping, env credential fallback or invocation of grant/revoke functions. This runs the pinned wrapper's lock timeout, the pinned SQL, and Alembic's revision update. Verify installed revision, table RLS, policies, ownership and complete effective function/table privileges afterward. A bare shell Alembic invocation is not sufficient project fencing.

Candidate separate technical-role appointment, only after migration acceptance and exact authorization:

```sql
CREATE ROLE safereturn_support_command
  NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE
  NOREPLICATION NOBYPASSRLS CONNECTION LIMIT 1;
GRANT CONNECT ON DATABASE postgres TO safereturn_support_command;
GRANT USAGE ON SCHEMA public TO safereturn_support_command;
GRANT safereturn_support_provisioner TO safereturn_support_command
  WITH ADMIN FALSE, INHERIT FALSE, SET TRUE;
```

This is a technical database role membership, not an application Support staff grant. Do not run it now. Refuse any preexisting name rather than adopting/altering an unknown login. Do not grant table/Auth/Storage access, other memberships or ADMIN OPTION. Audit PUBLIC capabilities and role membership closure before enabling login. The candidate appointment now includes CONNECTION LIMIT1 and explicit public-schema USAGE instead of relying on PUBLIC for name resolution; **this changes the proposed appointment package, not migration0044**. The exact credential storage/lifetime/rotation/closeout requirements are defined in the runbook: operator/SYSTEM-only DPAPI storage, unique SCRAM credential, <=60-minute per-operation password window, fixed verified TLS/session pooler, and tested session/ACL closeout. None has been provisioned or empirically verified against the pooler. No literal password or credential-generating command is supplied or executed here.

## Outstanding gates and final approval boundary

1. **Isolated environment/fixture authority:** authorize exactly one no-data Supabase preview branch `sr-support-0044-readiness`, with a distinct verified project reference, no merge/data copy/seed/parent mutation and <=24-hour resource lifetime plus approved provider charge. Availability is unverified; if unsupported, stop before any alternative. Reconcile its data-free0043 managed schema/custom roles from reviewed definitions, never a customer backup. Dashboard branches do not automatically capture dashboard-created custom roles; verify that baseline. [Supabase branching limitations](https://supabase.com/docs/guides/deployment/branching/dashboard).
2. **Actual enforcement tests:** current prohibitions still exclude creating credentials/identities/Support grants. To test positive command behavior on that disposable target, approval must expressly allow a disposable-only restricted command credential, owner-operated genuine provider email/TOTP for the fixed-email subject and test-only grant/revoke/audit/receipt transactions. The runbook specifies the exact test assertions, including negative role/table/function privilege checks without invoking QR functions. Additional fixture identities/cases need a reviewed exact manifest. No authorization transfers to the real development project. The CLI project pin must not be relaxed for the branch. No test driver has yet been validated on a suitable target; prepared assertions are not results.
3. **Deployment and recovery execution:** the read-only recovery assessment is implemented and its0043 path verified. Post-installation history inspection, atomic migration failure/unknown commit, original-key command replay, credential closeout and revocation procedure still require disposable rehearsal. The source-safe recovery path retains0044 history and uses forward repair; downgrade intentionally raises. A fully guarded deployment runner must be finalized/verified on that target before Cloud authorization. Password VALID UNTIL is only password expiry, not termination of sessions or staff authority. [PostgreSQL CREATE ROLE](https://www.postgresql.org/docs/17/sql-createrole.html).
4. **Before any live grant (distinct from empty schema installation):** bind the actual verified UUID, owner permit and running backend fence; settle actual protected storage/ACLs, named receipt-key custody, and the still unspecified numeric packet/receipt retention/disposal decision. Existing specs do not authorize inventing that period. All genuine provider/Support API/admission gates remain.

The smallest supported missing step is therefore the no-data managed preview environment and its exact disposable fixture/testing authorization, **not running0044 on fhuxryfkfrvycsojkzvq or repeating offline tests**. The preserved standalone cluster is not repurposed; no local Docker/bootstrap task is opened. If the owner keeps the no-identity/no-grant/no-credential prohibition for disposable targets too, positive command tests remain impossible under that scope; schema/negative tests alone cannot yield READY.

**Final Cloud execution authorization is WITHHELD, not offered for approval yet.** Only after the required real outcomes pass should an exact final authorization identify the above unchanged0044 hashes, the reviewed deployment runner and revised least-privilege appointment/credential package, targeting only fhuxryfkfrvycsojkzvq. It must exclude Auth signup/email/MFA changes, application Support grants/commands, frontend activation and Phase10. This preparation authorization does not permit any of those operations. No independent third-person signature is required by v1.1.
