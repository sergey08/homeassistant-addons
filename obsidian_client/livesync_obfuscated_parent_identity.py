"""Legacy LiveSync path ID fixture, offline only.

Upstream path2id_base derives f: + SHA256(SHA256(passphrase) + ':' +
normalised_path) when usePathObfuscation is enabled and keyed ID
derivation is absent. This fixture intentionally refuses keyed IDs.
"""
import hashlib
from livesync_write_preflight import validate_write_request, UnsafeWrite

def legacy_obfuscated_parent_id(path, passphrase, *, case_insensitive=True,
                                id_derivation_key=None):
    validate_write_request(path, "", None, creating=True)
    if id_derivation_key is not None:
        raise UnsafeWrite("keyed_id_derivation_not_supported")
    if not isinstance(passphrase,str) or not passphrase:
        raise UnsafeWrite("missing_obfuscation_passphrase")
    if type(case_insensitive) is not bool:
        raise UnsafeWrite("invalid_case_mode")
    normalized=path.lower() if case_insensitive else path
    inner=hashlib.sha256(passphrase.encode("utf-8")).hexdigest()
    outer=hashlib.sha256((inner+":"+normalized).encode("utf-8")).hexdigest()
    return "f:"+outer
