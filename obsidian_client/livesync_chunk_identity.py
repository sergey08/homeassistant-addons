"""Pure helpers for the legacy LiveSync XXHash64 chunk-ID input contract.

Does NOT compute IDs: upstream uses a mixed hash of a passphrase and
xxhash-wasm-102. Keep remote writes disabled until verified against a
pinned official CLI fixture. No credentials or real vault data required.
"""


def js_utf16_code_units(text: str) -> int:
    """Match JavaScript string.length, including surrogate pairs."""
    if not isinstance(text, str):
        raise TypeError("chunk text must be a string")
    return len(text.encode("utf-16-le", errors="surrogatepass")) // 2


def legacy_xxhash64_input(chunk_text: str, hashed_passphrase: str) -> bytes:
    """Form the bytes given to xxHash64, not the final content-derived ID."""
    if not isinstance(chunk_text, str) or not isinstance(hashed_passphrase, str):
        raise TypeError("hash inputs must be strings")
    framed = f"{chunk_text}-{hashed_passphrase}-{js_utf16_code_units(chunk_text)}"
    return framed.encode("utf-8", errors="surrogatepass")
