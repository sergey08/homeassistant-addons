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

## Confirmed independent read after Python parent update

CI job 125252712537 (run 41438061484) printed both:
- `Official CLI decoded Python-encrypted leaf with original IDs`
- `Official CLI decoded Python-updated parent and encrypted leaf`

The Python test changed the existing official parent document's `mtime`
using CouchDB's current `_rev`, while retaining its original identity,
and a fresh independent CLI `sync` + `cat` returned exactly the
Python-replacement content. This establishes compatibility for this
specific parent metadata update, **not** creation of independent notes.

The next assertion still fails for the independently generated
synthetic parent/leaf. To determine root cause, compare the pinned
upstream `path2id_base` path transformation and official chunk-ID
derivation, then test a new note using those algorithms. Do not
enable production writes or silently bypass the failing assertion.

## Content-addressed IDs verified (CI run 41470968252)

Two distinct notes containing *identical plaintext*, created by the
pinned official CLI, referenced exactly the same Chunk ID. This
confirms deterministic content-derived IDs for the active CI settings.
A copied official encrypted Chunk given an arbitrary new ID was not
readable by a fresh official client. Therefore random IDs are not
interoperable, even when the ciphertext and document shape are retained.

Next implementation task: identify the **pinned Commonlib HashManager**
algorithm and settings used by the CLI to compute IDs, compare Python
output to a known official fixture without logging source content or
identifiers, and only then re-run independent note creation. Keep the
existing failure assertion as a gate.
