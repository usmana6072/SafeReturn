# Retired admin prototypes

Synthetic records and pure prototype helpers live here only for historical test
fixtures. Production code in `app`, `components`, and `lib` must never import this
directory. The admin portal loads authorized backend data and reports unavailable
contracts explicitly; it cannot load a local demo database or switch roles.

The former prototype browser tests are retained as `.legacy.ts` modules and are
not collected as the current browser suite. Current owner/navigation tests are
in `tests/owner-roles.spec.ts`; live API and workflow tests remain active.
