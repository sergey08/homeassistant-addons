"""Explicit, bounded G-code upload to Moonraker; NEVER starts a print.

Caller must obtain approval for this exact file before invoking the upload.
No remote URL fetching, arbitrary roots, or printer movement.
"""
import hashlib
import json
import urllib.request

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
    if b"\x00" in content[:4096]:
        raise UploadError("Binary input refused")
    # Deliberately do not use Moonraker's print=true upload parameter.
    boundary = "moonraker-safe-upload-boundary"
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
        raise UploadError("Upload not confirmed")
    received = result["result"]
    if received.get("root") != "gcodes" or received.get("item", {}).get("path") != filename:
        raise UploadError("Uploaded path differs from requested path")
    return {"uploaded": True, "filename": filename, "sha256_local": digest,
            "size_bytes": len(content), "print_started": False,
            "note": "Verify remote metadata and file bytes separately before authorizing a print."}
