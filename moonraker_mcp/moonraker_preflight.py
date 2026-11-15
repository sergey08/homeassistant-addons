"""Conservative preflight checks for Snapmaker U1 G-code metadata.

Pure validation: no Moonraker writes, movement, or network operations.
"""
import math
from moonraker_files import validate_filename, FileAccessError

class PreflightError(ValueError):
    pass

def validate_u1_metadata(filename, metadata):
    try:
        validate_filename(filename)
    except FileAccessError as exc:
        raise PreflightError("Invalid filename") from exc
    if not filename.lower().endswith((".gcode", ".gco")):
        raise PreflightError("Only G-code files are accepted")
    if not isinstance(metadata, dict):
        raise PreflightError("Metadata unavailable")
    size = metadata.get("size")
    if type(size) not in (int, float) or not math.isfinite(size) or size <= 0:
        raise PreflightError("Invalid G-code size")
    # Slicer estimates are advisory, never proof of physical compatibility.
    for field in ("estimated_time", "layer_count", "object_height"):
        value = metadata.get(field)
        if value is not None and (type(value) not in (int, float)
                                  or not math.isfinite(value) or value < 0):
            raise PreflightError("Invalid " + field)
    diameters = metadata.get("nozzle_diameter_list", metadata.get("nozzle_diameter"))
    if diameters is not None:
        values = diameters if isinstance(diameters, list) else [diameters]
        if not values or len(values) > 4 or any(
            type(v) not in (int, float) or not math.isfinite(v) or v <= 0 or v > 2
            for v in values
        ):
            raise PreflightError("Invalid nozzle diameters")
    return {
        "filename": filename, "size_bytes": size,
        "estimated_time_s": metadata.get("estimated_time"),
        "layer_count": metadata.get("layer_count"),
        "object_height_mm": metadata.get("object_height"),
        "requires_human_confirmation": True,
        "compatible_with_u1": "unverified",
        "safe_to_start": False,
        "note": "Metadata alone cannot establish printer compatibility or a clear build plate.",
    }
