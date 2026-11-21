# Database-assigned owner access

`owner` inherits every current admin capability and staff-role authorization.
It is a SafeReturn application role in `public.staff_roles`, not a Supabase
database login or a value trusted from editable Auth user metadata.

Migration `0060_owner_role` defines the role without inserting or changing any
staff grant. No email, user ID or existing account is selected for owner access.
It was rehearsed with rollback, then applied and independently verified on the
configured Supabase project on 2026-11-21. Existing staff grants remained unchanged.
The scoped release script verifies existing staff rows are byte-for-byte
equivalent through an aggregate fingerprint, along with existing function ACLs,
table privileges and unrelated migration heads.

Verified email, current MFA, recent authentication where required, financial
eligibility, workflow state, case scope and independent approval checks remain.
The role grants authorization to implemented functions; it does not turn an
unimplemented or disabled integration into an available service.

The portal reads current database roles through `/api/v1/me/staff-security`.
Its navigation uses the returned capabilities. For existing explicit role
checks, owner has the effective staff roles; the header and own-security panel
display the assigned database role. There is no role dropdown, preview mode or
client-side role override. Existing non-owner roles retain their scoped access.
Revocation is enforced by the next backend request, and page loads refresh the
server-side security state without a persistent role cache.

The admin demo database and its policies have moved out of production modules
into `frontend/tests/fixtures/legacy-admin`. Prototype screens and role switching
have been removed. Retired prototype tests use `.legacy.ts`; current live-contract
and workflow tests remain active. Production modules must never import those
fixtures. Unsupported legacy API placeholders now return an unavailable error
instead of fabricated success or empty database results.

Release from the repository root, with `PYTHONPATH=backend`:

```powershell
backend/.venv/Scripts/python.exe backend/scripts/release_owner_role.py
backend/.venv/Scripts/python.exe backend/scripts/release_owner_role.py --apply
```

The default is a rollback rehearsal. `--apply` commits only after checking grant
preservation. Neither command assigns owner to an account.

Validation: `tests/test_staff_security.py`, `tests/integration/test_owner_role_local.py`,
the disposable owner order/payment/printing/shipment workflow (set
`SAFERETURN_OWNER_WORKFLOW_REHEARSAL=1`), `frontend/tests/owner-roles.spec.ts`,
TypeScript and the frontend production build. All enrolled identities in these
tests are synthetic and confined to disposable local databases or browser mocks.
