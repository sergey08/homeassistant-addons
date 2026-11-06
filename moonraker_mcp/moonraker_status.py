"""Read-only printer availability probe with bounded timeouts and safe output.

An unreachable endpoint cannot prove that the printer is switched off:
it may be unplugged, disconnected or experiencing a network problem.
"""
import json
import urllib.error
import urllib.request


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def connection_status(url, api_key="", timeout=4):
    """Query Moonraker /server/info without changing printer state."""
    base = url.rstrip("/")
    if not base.startswith(("http://", "https://")):
        return {"state": "unavailable", "message": "Moonraker URL is invalid."}
    headers = {"Accept": "application/json"}
    if api_key:
        headers["X-Api-Key"] = api_key
    req = urllib.request.Request(base + "/server/info", headers=headers)
    try:
        with _OPENER.open(req, timeout=timeout) as res:
            if res.status != 200:
                return {"state": "unavailable", "message": "Moonraker did not respond successfully."}
            raw = res.read(65537)
        if len(raw) > 65536:
            return {"state": "unavailable", "message": "Moonraker returned an oversized response."}
        data = json.loads(raw)
        info = data.get("result") if isinstance(data, dict) else None
        if not isinstance(info, dict):
            raise ValueError("Invalid Moonraker JSON response")
        klippy = info.get("klippy_state")
        if klippy == "ready":
            return {"state": "online", "klippy_state": "ready",
                    "message": "La impresora esta encendida y Moonraker responde."}
        return {"state": "not_ready", "klippy_state": str(klippy)[:64] if klippy is not None else "unknown",
                "message": "Moonraker responde, pero Klippy no esta listo."}
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            return {"state": "authentication_error",
                    "message": "Moonraker responde, pero rechaza la autenticacion."}
        return {"state": "unavailable",
                "message": "Moonraker ha respondido con un error HTTP."}
    except (urllib.error.URLError, TimeoutError, OSError):
        return {"state": "offline_or_unreachable",
                "message": "No se puede contactar con Moonraker. La impresora podria estar apagada o desconectada; comprueba su alimentacion y la red."}
    except (ValueError, UnicodeError):
        return {"state": "unavailable", "message": "Moonraker devolvio una respuesta no valida."}


def public_printer_info(url, api_key="", timeout=4):
    """Expose only state and software version, never hostnames or file paths.

    Query the real Moonraker API directly through a bounded, no-redirect GET.
    When the printer is offline or authorization fails, return a safe status
    instead of propagating internal URLs or exception text.
    """
    base = url.rstrip("/")
    if not base.startswith(("http://", "https://")):
        return {"state": "unavailable"}
    headers = {"Accept": "application/json"}
    if api_key:
        headers["X-Api-Key"] = api_key
    req = urllib.request.Request(base + "/printer/info", headers=headers)
    try:
        with _OPENER.open(req, timeout=timeout) as res:
            if res.status != 200:
                return {"state": "unavailable"}
            raw = res.read(65537)
        if len(raw) > 65536:
            return {"state": "unavailable"}
        data = json.loads(raw)
        info = data.get("result") if isinstance(data, dict) else None
        if not isinstance(info, dict):
            raise ValueError("Invalid Moonraker printer info")
        state = info.get("state", "unknown")
        if not isinstance(state, str) or state not in (
                "ready", "startup", "shutdown", "error", "disconnected"):
            state = "unknown"
        result = {"state": state}
        version = info.get("software_version")
        # Version may be an arbitrary upstream string; allow only a tightly
        # bounded version-shaped ASCII value without internal paths/URLs.
        if (isinstance(version, str) and 0 < len(version) <= 100
                and all(ch.isalnum() or ch in ".+_:-" for ch in version)
                and version.isascii()):
            result["software_version"] = version
        return result
    except urllib.error.HTTPError as exc:
        return {"state": ("authentication_error" if exc.code in (401, 403)
                          else "unavailable")}
    except (urllib.error.URLError, TimeoutError, OSError):
        return {"state": "offline_or_unreachable"}
    except (ValueError, UnicodeError):
        return {"state": "unavailable"}


def public_server_info(url, api_key="", timeout=4):
    """Return a minimal Moonraker health snapshot without component names.

    Server warnings, component lists and free-form diagnostic strings are
    intentionally not forwarded to remote MCP clients.
    """
    base = url.rstrip("/")
    if not base.startswith(("http://", "https://")):
        return {"state": "unavailable"}
    headers = {"Accept": "application/json"}
    if api_key:
        headers["X-Api-Key"] = api_key
    req = urllib.request.Request(base + "/server/info", headers=headers)
    try:
        with _OPENER.open(req, timeout=timeout) as res:
            if res.status != 200:
                return {"state": "unavailable"}
            raw = res.read(65537)
        if len(raw) > 65536:
            return {"state": "unavailable"}
        data = json.loads(raw)
        info = data.get("result") if isinstance(data, dict) else None
        if not isinstance(info, dict):
            raise ValueError("Invalid server status")
        response = {}
        version = info.get("moonraker_version")
        if (isinstance(version, str) and 0 < len(version) <= 80
                and version.isascii()
                and all(ch.isalnum() or ch in ".+_:-" for ch in version)):
            response["moonraker_version"] = version
        connected = info.get("klippy_connected")
        if isinstance(connected, bool):
            response["klippy_connected"] = connected
        klippy_state = info.get("klippy_state")
        if isinstance(klippy_state, str) and klippy_state in (
                "ready", "startup", "shutdown", "error", "disconnected"):
            response["klippy_state"] = klippy_state
        api_version = info.get("api_version_string")
        if (isinstance(api_version, str) and 0 < len(api_version) <= 32
                and api_version.isascii()
                and all(ch.isdigit() or ch == "." for ch in api_version)):
            response["api_version_string"] = api_version
        if not response:
            return {"state": "unavailable"}
        return response
    except urllib.error.HTTPError as exc:
        return {"state": "authentication_error" if exc.code in (401, 403) else "unavailable"}
    except (urllib.error.URLError, TimeoutError, OSError):
        return {"state": "offline_or_unreachable"}
    except (ValueError, UnicodeError):
        return {"state": "unavailable"}


def public_temperature_store(url, api_key="", timeout=5):
    """Expose recent heater telemetry only, without arbitrary sensor names.

    Limit each series to the latest 120 finite numeric readings. Nonstandard
    sensor names are replaced by deterministic generic identifiers, because
    user-created sensor names can contain personal or internal details.
    """
    import math
    import re
    base = url.rstrip("/")
    if not base.startswith(("http://", "https://")):
        return {"state": "unavailable"}
    headers = {"Accept": "application/json"}
    if api_key:
        headers["X-Api-Key"] = api_key
    req = urllib.request.Request(base + "/server/temperature_store", headers=headers)
    try:
        with _OPENER.open(req, timeout=timeout) as res:
            if res.status != 200:
                return {"state": "unavailable"}
            raw = res.read(262145)
        if len(raw) > 262144:
            return {"state": "unavailable"}
        data = json.loads(raw)
        source = data.get("result") if isinstance(data, dict) else None
        if not isinstance(source, dict) or len(source) > 32:
            raise ValueError("Invalid temperature data")
        result = {}
        unnamed = 0
        for key, series in sorted(source.items()):
            if not isinstance(key, str) or not isinstance(series, dict):
                raise ValueError("Invalid sensor data")
            if re.fullmatch(r"extruder[0-9]{0,2}|heater_bed", key):
                visible_name = key
            else:
                unnamed += 1
                visible_name = "sensor_" + str(unnamed)
            if visible_name in result:
                raise ValueError("Duplicate sensor output name")
            public = {}
            for field in ("temperatures", "targets", "powers"):
                values = series.get(field)
                if values is None:
                    continue
                if not isinstance(values, list) or len(values) > 2400:
                    raise ValueError("Invalid temperature series")
                last_values = values[-120:]
                if not all(type(v) in (int, float) and math.isfinite(v)
                           and -100000 <= v <= 100000 for v in last_values):
                    raise ValueError("Invalid temperature readings")
                public[field] = last_values
            if public:
                result[visible_name] = public
        return result if result else {"state": "unavailable"}
    except urllib.error.HTTPError as exc:
        return {"state": "authentication_error" if exc.code in (401, 403) else "unavailable"}
    except (urllib.error.URLError, TimeoutError, OSError):
        return {"state": "offline_or_unreachable"}
    except (ValueError, UnicodeError, TypeError):
        return {"state": "unavailable"}
