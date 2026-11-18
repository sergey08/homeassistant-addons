"""Explicit, bounded G-code upload to Moonraker; NEVER starts a print.

Caller must obtain approval for this exact file before invoking the upload.
No remote URL fetching, arbitrary roots, or printer movement.
"""
import hashlib
import json
import secrets
import urllib.request
import urllib.parse

from moonraker_files import FileAccessError, _NoRedirect, validate_base_url, validate_filename

MAX_UPLOAD_BYTES = 32 * 1024 * 1024
MAX_REPLY_BYTES = 16384

class UploadError(ValueError):
    pass

def upload_gcode(base_url, filename, content, expected_sha256, api_key="", opener=None):
    if not isinstance(filename, str) or "/" in filename:
        raise UploadError("Only flat filenames allowed")
    try:
        validate_filename(filename)
        base = validate_base_url(base_url)
    except FileAccessError as exc:
        raise UploadError("Invalid filename or printer URL") from exc
    if any(ch in filename for ch in ('"', ';')):
        raise UploadError("Unsafe multipart filename")
    if not filename.lower().endswith((".gcode", ".gco")):
        raise UploadError("Only G-code accepted")
    if type(content) is not bytes or not 0 < len(content) <= MAX_UPLOAD_BYTES:
        raise UploadError("Invalid G-code size")
    digest = hashlib.sha256(content).hexdigest()
    if type(expected_sha256) is not str or len(expected_sha256) != 64 or digest != expected_sha256.lower():
        raise UploadError("SHA-256 mismatch")
    if b"\x00" in content:
        raise UploadError("Binary input refused")
    # Deliberately do not use Moonraker's print=true upload parameter.
    boundary = "moonraker-safe-" + secrets.token_hex(24)
    parts = [
        ('root', 'gcodes'),
        ('path', ''),
        ('print', 'false'),
    ]
    body = bytearray()
    for key, value in parts:
        body.extend(('--' + boundary + '\r\nContent-Disposition: form-data; name="' + key + '"\r\n\r\n' + value + '\r\n').encode())
    body.extend(('--' + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="' + filename + '"\r\nContent-Type: application/octet-stream\r\n\r\n').encode())
    body.extend(content)
    body.extend(('\r\n--' + boundary + '--\r\n').encode())
    headers = {"Accept": "application/json", "Content-Type": "multipart/form-data; boundary=" + boundary}
    if api_key:
        headers["X-Api-Key"] = api_key
    req = urllib.request.Request(base + "/server/files/upload", data=bytes(body), headers=headers, method="POST")
    if opener is None:
        opener = urllib.request.build_opener(_NoRedirect()).open
    with opener(req, timeout=30) as response:
        raw = response.read(MAX_REPLY_BYTES + 1)
    if len(raw) > MAX_REPLY_BYTES:
        raise UploadError("Response too large")
    try:
        result = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise UploadError("Invalid upload response") from exc
    if not isinstance(result, dict) or not isinstance(result.get("result"), dict):
        # Nonstandard upload responses must be independently verified.
        # Never infer success from HTTP 200 alone.
        remote_url = base + "/server/files/gcodes/" + urllib.parse.quote(filename, safe="")
        verify_headers = {"Accept": "application/octet-stream"}
        if api_key:
            verify_headers["X-Api-Key"] = api_key
        verify_req = urllib.request.Request(remote_url, headers=verify_headers, method="GET")
        verify_open = urllib.request.build_opener(_NoRedirect()).open
        with verify_open(verify_req, timeout=30) as remote_response:
            remote = remote_response.read(MAX_UPLOAD_BYTES + 1)
        if len(remote) != len(content) or hashlib.sha256(remote).hexdigest() != digest:
            raise UploadError("Remote G-code verification mismatch")
        return {"uploaded": True, "filename": filename, "sha256_local": digest,
                "sha256_remote_verified": digest, "size_bytes": len(content),
                "print_requested": False, "confirmation": "remote_sha256",
                "note": "Upload requested print=false; remote file verified; printer state unverified."}
    received = result["result"]
    item = received.get("item")
    if received.get("root") != "gcodes":
        raise UploadError("Upload response root mismatch")
    if not isinstance(item, dict):
        raise UploadError("Upload response missing item object")
    if item.get("path") != filename:
        raise UploadError("Upload response path mismatch")
    return {"uploaded": True, "filename": filename, "sha256_local": digest,
            "size_bytes": len(content), "print_requested": False,
            "note": "Upload requested print=false; printer state and remote file integrity are unverified."}
