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


# xxHash64, seed 0. Pure Python so the isolated test has no runtime
# dependency on native xxhash wheels.
_MASK=(1<<64)-1
_P1=11400714785074694791
_P2=14029467366897019727
_P3=1609587929392839161
_P4=9650029242287828579
_P5=2870177450012600261


def _rotl(x, n):
    return ((x << n) | (x >> (64-n))) & _MASK


def _round(acc, value):
    return (_rotl((acc + value*_P2) & _MASK, 31)*_P1) & _MASK


def xxhash64(data: bytes, seed: int = 0) -> int:
    """Reference-compatible xxHash64 unsigned integer."""
    if not isinstance(data, bytes):
        raise TypeError("xxhash64 accepts bytes")
    if not (0 <= seed <= _MASK):
        raise ValueError("invalid xxhash seed")
    n=len(data)
    pos=0
    if n>=32:
        v1=(seed+_P1+_P2)&_MASK
        v2=(seed+_P2)&_MASK
        v3=seed
        v4=(seed-_P1)&_MASK
        while pos<=n-32:
            vals=[int.from_bytes(data[pos+i:pos+i+8],"little") for i in (0,8,16,24)]
            v1=_round(v1,vals[0])
            v2=_round(v2,vals[1])
            v3=_round(v3,vals[2])
            v4=_round(v4,vals[3])
            pos+=32
        h=(_rotl(v1,1)+_rotl(v2,7)+_rotl(v3,12)+_rotl(v4,18))&_MASK
        for v in (v1,v2,v3,v4):
            h=((h ^ _round(0,v))*_P1+_P4)&_MASK
    else:
        h=(seed+_P5)&_MASK
    h=(h+n)&_MASK
    while pos+8<=n:
        k=_round(0,int.from_bytes(data[pos:pos+8],"little"))
        h=(_rotl(h ^ k,27)*_P1+_P4)&_MASK
        pos+=8
    if pos+4<=n:
        h=(_rotl(h ^ (int.from_bytes(data[pos:pos+4],"little")*_P1&_MASK),23)*_P2+_P3)&_MASK
        pos+=4
    while pos<n:
        h=(_rotl(h ^ (data[pos]*_P5&_MASK),11)*_P1)&_MASK
        pos+=1
    h^=h>>33
    h=(h*_P2)&_MASK
    h^=h>>29
    h=(h*_P3)&_MASK
    h^=h>>32
    return h


def base36_unsigned(value: int) -> str:
    if not isinstance(value,int) or not 0<=value<=_MASK:
        raise ValueError("expected unsigned 64-bit integer")
    digits="0123456789abcdefghijklmnopqrstuvwxyz"
    if value==0:
        return "0"
    result=""
    while value:
        value,rem=divmod(value,36)
        result=digits[rem]+result
    return result


def legacy_xxhash64_digest(chunk_text: str, hashed_passphrase: str) -> str:
    """Digest only; caller must supply upstream-derived passphrase hash.

    Does not invent a full remote document ID; validate the namespace and
    hash against the pinned CLI before using this for writes.
    """
    return base36_unsigned(xxhash64(
        legacy_xxhash64_input(chunk_text,hashed_passphrase)))


def _js_uint32(value):
    import math
    if not math.isfinite(value) or value == 0:
        return 0
    return math.trunc(value) & 0xffffffff


def _js_int32(value):
    value = _js_uint32(value)
    return value if value < (1 << 31) else value - (1 << 32)


def fallback_mixed_hash_each(source: str) -> str:
    """Port of octagonal-wheels/hash/purejs fallbackMixedHashEach.

    Replicates JavaScript's signed bitwise operations and floating-point
    multiplications. This is a non-cryptographic obfuscation hash.
    """
    if not isinstance(source, str):
        raise TypeError("source must be text")
    raw = f"{js_utf16_code_units(source)}{source}"
    b = raw.encode("utf-16-le", errors="surrogatepass")
    units = (int.from_bytes(b[i:i + 2], "little") for i in range(0, len(b), 2))
    h = 1
    fnv = 2166136261
    count = js_utf16_code_units(raw)
    for code in units:
        fnv = ((fnv ^ code) * 0x01000193) & 0xffffffff
        k = _js_uint32(float(code * 0xcc9e2d51))
        k = _js_int32((k << 15) | (_js_uint32(k) >> 17))
        k = _js_int32(float(k * 0x1b873593))
        h = _js_int32(_js_uint32(h) ^ k)
        h = _js_int32((h << 13) | (_js_uint32(h) >> 19))
        h = float(h * 5 + 0xe6546b64)
    h = _js_int32(_js_uint32(h) ^ count)
    h = _js_int32(h ^ (_js_uint32(h) >> 16))
    h = _js_int32(h * 0x85ebca6b)
    h = _js_int32(h ^ (_js_uint32(h) >> 13))
    h = _js_int32(h * 0xc2b2ae35)
    h = _js_int32(h ^ (_js_uint32(h) >> 16))
    return base36_unsigned(_js_uint32(h)) + base36_unsigned(fnv)


_LEGACY_ID_SALT = "a83hrf7f\x03y7sa8g31"


def legacy_chunk_id(chunk_text: str, passphrase: str) -> str:
    """Legacy encrypted XXHash64 ID for verification, NOT a writer API.

    Uses the observed Commonlib HashManagerCore derivation. Does not
    support independently keyed IDs (idDerivationVersion=1).
    """
    if not isinstance(chunk_text, str) or not isinstance(passphrase, str):
        raise TypeError("chunk and passphrase must be strings")
    units=passphrase.encode("utf-16-le", errors="surrogatepass")
    prefix_length=(js_utf16_code_units(passphrase)*3)//4
    excerpt=units[:prefix_length*2].decode("utf-16-le",errors="surrogatepass")
    passphrase_hash=fallback_mixed_hash_each(_LEGACY_ID_SALT+excerpt)
    return "+"+legacy_xxhash64_digest(chunk_text,passphrase_hash)
