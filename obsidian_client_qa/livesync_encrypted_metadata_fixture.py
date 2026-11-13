"""Offline LiveSync HKDF encrypted-parent metadata *fixture* codec.

Reproduces upstream encryption.ts metadata payload and zeroed outer fields.
Does not derive obfuscated _id and cannot issue network requests. Callers
must NOT use this as a production writer.
"""
import json
from livesync_crypto import encrypt_hkdf_string, decrypt_hkdf_string
from livesync_write_preflight import validate_write_request, UnsafeWrite


def encode_parent_metadata_fixture(path, children, passphrase, pbkdf2_salt_b64,
                                   *, ctime, mtime, size):
    validate_write_request(path, "", None, creating=True)
    if (not isinstance(children,list) or not children or len(children)>512
            or any(not isinstance(x,str) or not x.startswith("h:+") for x in children)
            or len(set(children))!=len(children)):
        raise UnsafeWrite("invalid_children")
    if any(type(value) is not int or value<0 for value in (ctime,mtime,size)):
        raise UnsafeWrite("invalid_parent_fields")
    # upstream encryptMetaWithHKDF: JSON.stringify({path,mtime,ctime,size,children})
    metadata={"path":path,"mtime":mtime,"ctime":ctime,
              "size":size,"children":list(children)}
    plaintext=json.dumps(metadata,ensure_ascii=False,separators=(",",":"))
    encrypted="/\\:"+encrypt_hkdf_string(plaintext,passphrase,pbkdf2_salt_b64)
    return {"path":encrypted,"mtime":0,"ctime":0,"size":0,
            "children":[],"write_supported":False}


def decode_parent_metadata_fixture(ciphertext, passphrase, pbkdf2_salt_b64):
    if not isinstance(ciphertext,str) or not ciphertext.startswith("/\\:%="):
        raise UnsafeWrite("invalid_encrypted_metadata")
    decoded=json.loads(decrypt_hkdf_string(
        ciphertext[3:],passphrase,pbkdf2_salt_b64))
    if not isinstance(decoded,dict) or set(decoded)!={"path","mtime","ctime","size","children"}:
        raise UnsafeWrite("unexpected_metadata_fields")
    return decoded
