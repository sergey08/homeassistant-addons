"""Read-only Home Assistant Ingress Markdown browser."""
import html
import json
import os
from pathlib import Path
from urllib.parse import quote

import markdown
from flask import Flask, Response, abort, request

app = Flask(__name__)


def root_dir():
    config = Path("/data/options.json")
    try:
        options = json.loads(config.read_text()) if config.is_file() else {}
    except (OSError, ValueError):
        options = {}
    root = Path(options.get("vault_path", "/share/obsidian-client/vault")).resolve()
    if not root.is_relative_to(Path("/share").resolve()):
        abort(400, "Vault path must be inside /share")
    return root


def page(contents):
    return """<!doctype html><html lang="es"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <style>:root{color-scheme:light dark}body{max-width:900px;margin:auto;padding:24px;
    background:Canvas;color:CanvasText;font:16px system-ui,sans-serif}
    a{color:#8070e0}article{line-height:1.65;overflow-wrap:anywhere}
    pre{overflow:auto;background:#8882;padding:12px}input{width:100%;padding:10px;box-sizing:border-box}
    li{margin:10px 0}</style></head><body>""" + contents + "</body></html>"


@app.get("/")
def home():
    root = root_dir()
    if not root.is_dir():
        return page("<h1>Obsidian Client</h1><p>No se encuentra la carpeta de notas. "
                    "Configura vault_path dentro de /share.</p>")
    relative = request.args.get("path")
    if relative is not None:
        if "\\\\" in relative or "\x00" in relative:
            abort(400)
        target = (root / relative).resolve()
        if not target.is_relative_to(root) or target.suffix.lower() != ".md" or not target.is_file():
            abort(404)
        content = target.read_text(encoding="utf-8", errors="replace")
        rendered = markdown.markdown(html.escape(content), extensions=["tables", "fenced_code"])
        return page('<p><a href="./">← Volver</a></p><h1>' + html.escape(target.stem) +
                    '</h1><article>' + rendered + '</article>')
    term = request.args.get("q", "").strip().casefold()
    paths = []
    for p in root.rglob("*.md"):
        relative = p.relative_to(root)
        if any(part.startswith(".") for part in relative.parts):
            continue
        if term and term not in str(relative).casefold():
            continue
        paths.append(relative.as_posix())
        if len(paths) >= 2000:
            break
    paths.sort(key=str.casefold)
    rows = "".join('<li><a href="?path=' + quote(p, safe="") + '">' +
                   html.escape(p) + "</a></li>" for p in paths)
    return page('<h1>Obsidian Client</h1><p>Vista preliminar de solo lectura (' +
                str(len(paths)) + ' notas)</p><form><input name="q" placeholder="Buscar notas" value="' +
                html.escape(request.args.get("q", ""), quote=True) + '"></form><ul>' + rows + "</ul>")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8099)
