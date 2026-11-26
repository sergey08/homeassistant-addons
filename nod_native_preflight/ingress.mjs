import http from 'node:http';

import { pipeline } from 'node:stream';

// The UI bundle is served by Nod on loopback. Only generated Vite assets
// qualify here. Session, uploads and API routes use separate handlers.
function isBundleAsset(path) {
  return /^\/assets\/[A-Za-z0-9_-]+\.(?:js|css|woff2?|png|svg)(?:\?v=[A-Za-z0-9_-]+)?$/.test(path);
}

function serveBundleAsset(req, res, port = 4310) {
  if (!isBundleAsset(req.url) || !['HEAD', 'GET'].includes(req.method)) {
    res.writeHead(404).end();
    return;
  }
  const upstream = http.request({
    hostname: '127.0.0.1', port, path: req.url, method: req.method,
    headers: { 'Accept-Encoding': 'identity' },
  }, reply => {
    if (reply.statusCode !== 200 || !reply.headers['content-type'] ||
        reply.headers['content-type'].startsWith('text/html')) {
      reply.resume();
      res.writeHead(reply.statusCode === 404 ? 404 : 502).end();
      return;
    }
    res.writeHead(200, {
      'Content-Type': reply.headers['content-type'],
      'X-Content-Type-Options': 'nosniff',
      'Cache-Control': 'private, no-store',
    });
    pipeline(reply, res, () => {});
  });
  res.once('close', () => upstream.destroy());
  upstream.setTimeout(15000, () => upstream.destroy(new Error('Asset timeout')));
  upstream.on('error', () => {
    if (!res.headersSent && !res.destroyed) res.writeHead(502).end();
  });
  upstream.end();
}

const nodOrigin = process.env.NOD_INGRESS_NOD_ORIGIN || '';
const haOrigin = process.env.NOD_INGRESS_HA_ORIGIN || '';
function validOrigin(value) {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && url.origin === value;
  } catch { return false; }
}
const embed = validOrigin(nodOrigin) && validOrigin(haOrigin) && nodOrigin !== haOrigin;
if ((nodOrigin || haOrigin) && !embed) throw Error('Invalid embedded panel origins');
const html = value => value.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const page = embed
  ? `<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Nod</title><style>html,body{margin:0;height:100%;font:14px system-ui;color-scheme:light dark}main{display:flex;flex-direction:column;height:100%}header{padding:8px 12px;text-align:right}a{color:inherit}iframe{border:0;flex:1;min-height:0;width:100%}</style></head><body><main><header><a href="${html(nodOrigin)}/" target="_blank" rel="noopener noreferrer">Abrir Nod en otra pestaña ↗</a></header><iframe title="Nod" src="${html(nodOrigin)}/" referrerpolicy="no-referrer" sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox allow-downloads"></iframe></main></body></html>`
  : `<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Nod — diagnóstico</title></head><body><main><h1>Nod nativo</h1><p>Servidor y PostgreSQL: comprobación de arranque superada.</p><p>Modo experimental. Activa el panel integrado en la configuración cuando esté disponible.</p></main></body></html>`;
const server = http.createServer((req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Referrer-Policy', 'no-referrer');
  res.setHeader('Content-Security-Policy', "default-src 'none'; frame-ancestors 'self'; base-uri 'none'; form-action 'none'" + (embed ? "; style-src 'unsafe-inline'; frame-src " + nodOrigin : ""));
  if (req.socket.remoteAddress !== '172.30.32.2') {
    res.writeHead(403).end('Forbidden');
    return;
  }
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.writeHead(405, {Allow: 'GET, HEAD'}).end();
    return;
  }
  if (!embed && isBundleAsset(req.url)) {
    serveBundleAsset(req, res);
    return;
  }
  if (req.url !== '/') {
    res.writeHead(404).end();
    return;
  }
  res.writeHead(200, {'Content-Type':'text/html; charset=utf-8'});
  res.end(req.method === 'HEAD' ? undefined : page);
});
server.headersTimeout = 5000;
server.requestTimeout = 10000;
server.maxHeadersCount = 32;
server.listen(8099, '0.0.0.0', () => console.log('NOD_NATIVE_INGRESS_LISTENING'));
