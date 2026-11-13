# Obsidian Client — security and readiness audit (2026-11-04)

## Scope

Static review of the repository's development add-on: `config.yaml`,
`Dockerfile`, `server.py`, `livesync_cli_bridge.py`,
`couchdb_cas.py`, `livesync_write_preflight.py`,
`livesync_revision_contract.py` and the disposable orphan auditor.
This is **not** a penetration test, a production validation or approval
to access a real user's vault.

## Verified architecture

- The add-on remains **experimental**, `0.1.0-dev93`, with manual startup.
- The Home Assistant `/share` mount is read-only; the CLI's local database
  is separate in `/data/livesync-client`.
- The editor's `/api/livesync-cli/local-save` saves to the local CLI database
  only. `/api/remote/write-preview` checks the remote snapshot but does not
  submit an update.
- The bridge contains a `sync_configured_remote` function, but the
  production server does not expose it as a web route.
- `couchdb_cas.py` is a conditional PUT helper requiring an external
  wire-format validator; this is not an authorized end-to-end remote writer.
- The disposable orphan auditor is offline and explicitly returns
  `deletion_permitted: False`.

## High-priority issue discovered and addressed in this PR

The production `POST /api/livesync-cli/publish-test-note` route previously
called `publish_isolated_test_note` using the **configured** CouchDB remote,
and verified the result by reading the remote note. Although the note path
and contents were fixed, the request could create a remote note in the
configured vault. That contradicted the application's read-only safety
claims and could affect real vault data.

**Resolution:** the endpoint now always rejects publication with HTTP 403
`remote_writes_disabled`. Disposable encrypted publication must remain
in the isolated CI environment. An offline Flask route regression test
ensures the publishing bridge is never called.

## Remaining gates before any real bidirectional editing

1. Establish the exact LiveSync wire encoder, metadata and chunk invariants
   against the pinned upstream implementation. Unit preflight helpers alone
   do not prove compatibility.
2. Execute create/update/read and concurrent writer/conflict scenarios in
   a disposable encrypted CouchDB, including interruption and recovery.
3. Review ingress authorization, anti-CSRF controls, remote endpoint allowlist,
   secret handling and error/log sanitization before adding new write routes.
4. Design a separate explicit opt-in for an isolated test database, with
   hard limits and operator approval. Do **not** automatically enable writes
   to an existing LiveSync vault.

## Decision

**NO-GO** for general remote writes or destructive cleanup against a real
Obsidian vault. Read-only browsing, local-only edits and disposable tests
may continue. This audit does not authorize production publication.
