# LiveSync encrypted-write interoperability — experimental findings

Date: 2026-11-02. Source: PR #25, isolated GitHub Actions CouchDB job.
All test data is synthetic; production remote writes remain disabled.

## Verified

- The Python AES-GCM/HKDF codec can encrypt and decrypt synthetic metadata and leaf content on disposable CouchDB (PR #24).
- A second official LiveSync CLI instance cannot currently read the note inserted directly using our synthetic document representation (PR #25).
- The official CLI's own isolated note produces one `plain` and one `leaf` record in the sampled database.
- Sanitized extra document fields:
  - Official `plain`: `ctime`, `eden`, `mtime`, `size`, `type`.
  - Our synthetic `plain`: `size`, `type`.
  - Official `leaf`: `e_`, `type`.
  - Our synthetic `leaf`: `type`.
- The official leaf ID has a short prefixed shape; our arbitrary IDs do not match official derivation. Neither document IDs nor values are logged.

## Not established

The missing fields are differences, not proof that adding placeholders would make a valid LiveSync document. The official document-ID derivation, encrypted metadata envelope, child references, and replication metadata must be reproduced and verified against a second official client. Do not weaken the CI assertion or enable production writes.

## Next diagnostic

Compare **types and presence** of official `e_`, `eden`, `ctime`, `mtime`, child references and encrypted path envelope without logging any source values; then derive compatible IDs from the pinned upstream implementation and confirm independent CLI `sync` + `cat` in the disposable database.
