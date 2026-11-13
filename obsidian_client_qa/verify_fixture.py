"""Check an isolated LiveSync fixture / Verificar una muestra aislada.

Usage / Uso:
  python verify_fixture.py /path/to/test-fixture.json

Only use fixtures created in a NEW, EMPTY test vault and test CouchDB.
Never export personal notes or CouchDB credentials into a fixture or GitHub.
Fixture format:
{
  "parent": {"type":"plain","path":"Demo/Hello.md","children":["h:a"],"size":5},
  "chunks": {"h:a":{"type":"leaf","data":"Hello"}},
  "expected": {"path":"Demo/Hello.md","content":"Hello"}
}
"""
import json
import sys
from pathlib import Path

from livesync_plain import UnsupportedNote, decode_plain_note


def verify(fixture):
    if not isinstance(fixture, dict) or set(fixture) != {"parent", "chunks", "expected"}:
        raise ValueError("Invalid fixture fields / Campos incorrectos")
    expected = fixture["expected"]
    if not isinstance(expected, dict) or set(expected) != {"path", "content"}:
        raise ValueError("Invalid expected note / Nota esperada incorrecta")
    if not all(isinstance(value, str) for value in expected.values()):
        raise ValueError("Expected fields must be strings / Los valores deben ser texto")
    actual = decode_plain_note(fixture["parent"], fixture["chunks"])
    if actual != expected:
        raise AssertionError("Note differs from fixture / La nota difiere del ejemplo")
    return True


def main(argv):
    if len(argv) != 2:
        print("Usage / Uso: python verify_fixture.py test-fixture.json")
        return 2
    path = Path(argv[1])
    if path.stat().st_size > 3_000_000:
        print("Fixture too large / Ejemplo demasiado grande")
        return 2
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        verify(data)
    except (ValueError, KeyError, TypeError, UnsupportedNote, AssertionError) as exc:
        print("FAIL / FALLO:", type(exc).__name__)
        return 1
    print("PASS / CORRECTO: byte-identical note / nota idéntica")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
