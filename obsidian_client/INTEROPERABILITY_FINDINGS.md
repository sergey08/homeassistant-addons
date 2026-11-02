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

## Confirmed cross-client ciphertext interoperability

CI run 41436825443, isolated CouchDB: the official CLI successfully
decoded **Python-encrypted Markdown data** when the original official
leaf document ID, parent metadata and revision were retained. The
independent reader returned exactly the replacement content. This is a
positive integration test, not merely a Python self-roundtrip.

A *separately created* Python parent/leaf pair still fails the official
CLI's sync/cat compatibility assertion in the same job. The remaining
work is compatible parent/leaf identity and document metadata. Do not
claim end-to-end writer interoperability until the second assertion
passes.

The official client's example plain document contained an empty
`eden` object; its leaf's `e_` field is boolean. An empty `eden`
alone is not sufficient evidence for arbitrary-file compatibility.
