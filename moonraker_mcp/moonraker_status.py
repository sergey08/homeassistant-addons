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
