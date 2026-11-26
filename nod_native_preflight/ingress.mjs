import http from 'node:http';
import { readFileSync } from 'node:fs';

import { pipeline } from 'node:stream';

// The UI bundle is served by Nod on loopback. Only generated Vite assets
// qualify here. Session, uploads and API routes use separate handlers.
function isBundleAsset(path) {
  return /^\/assets\/[A-Za-z0-9_-]+\.(?:js|css|woff2?|png|svg)(?:\?v=[A-Za-z0-9_-]+)?$/.test(path);
}

const uiFiles = new Set(['/', '/theme-init.js', '/favicon.svg', '/favicon.ico', '/apple-touch-icon.png']);
function isPanelRead(path) {
  return uiFiles.has(path) || isBundleAsset(path) || path === '/api/session';
}

function servePanelRead(req, res, port = 4310) {
  if (!isPanelRead(req.url) || !['HEAD', 'GET'].includes(req.method)) {
    res.writeHead(404).end();
    return;
  }
  const upstream = http.request({
    hostname: '127.0.0.1', port, path: req.url, method: req.method,
    headers: { Host: upstreamHost, 'Accept-Encoding': 'identity',
      ...(req.url === '/api/session' ? { Cookie: backendCookie } : {}),
    },
  }, reply => {
    const type = (reply.headers['content-type'] || '').split(';')[0].trim();
    const session = req.url === '/api/session';
    const validType = req.url === '/' ? type === 'text/html' :
      session ? type === 'application/json' : type && type !== 'text/html';
    if (!validType || !(reply.statusCode === 200 || (session && reply.statusCode === 401))) {
      reply.resume();
      res.writeHead(reply.statusCode === 404 ? 404 : 502).end();
      return;
    }
    res.writeHead(reply.statusCode, {
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


function supervisorAdmin(req) {
  const groups = req.headers['x-remote-user-groups'];
  return Boolean(req.headers['x-remote-user-id']) && typeof groups === 'string' &&
    groups.split(',').includes('system-admin');
}

const chatReads = new Set(['/api/state', '/api/events', '/api/messages', '/api/preferences',
  '/api/apps', '/api/trust', '/api/onboarding/introduction', '/api/models',
  // Read-only settings views; sensitive detail and mutation routes remain denied.
  '/api/schedules', '/api/tasks', '/api/schedule-runs', '/api/apps/catalog',
  '/api/channels', '/api/trust/entries', '/api/vault/activity', '/api/vault', '/api/vault/sessions']);
const chatWrites = new Set(['/api/messages', '/api/account/welcome', '/api/onboarding/profile',
  '/api/onboarding/updates-email', '/api/onboarding/suggestions', '/api/account/model-setup', '/api/account/prepare']);

function serveChat(req, res, port = 4310) {
  const path = req.url.split('?')[0];
  const events = req.url.split('?')[0] === '/api/events';
  const write = req.method === 'POST';
  if (!((req.method === 'GET' && chatReads.has(path)) || (write && chatWrites.has(path)))) {
    res.writeHead(405).end();
    return;
  }
  if (write && (req.headers['x-nod-ingress-request'] !== '1' ||
      req.headers['content-type']?.split(';')[0] !== 'application/json')) {
    res.writeHead(403).end();
    return;
  }
  const headers = { Host: upstreamHost, Cookie: backendCookie };
  if (write) headers['Content-Type'] = 'application/json';
  if (req.headers['x-nod-account']) headers['X-Nod-Account'] = req.headers['x-nod-account'];
  const upstream = http.request({ hostname: '127.0.0.1', port, path: req.url,
    method: req.method, headers }, reply => {
    const type = reply.headers['content-type']?.split(';')[0];
    if (!(type === 'application/json' || (events && type === 'text/event-stream') || reply.statusCode === 204)) {
      reply.resume();
      res.writeHead(502).end();
      return;
    }
    res.writeHead(reply.statusCode, { 'Content-Type': type || 'application/json',
      'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no' });
    res.flushHeaders();
    pipeline(reply, res, () => {});
  });
  res.once('close', () => upstream.destroy());
  upstream.on('error', () => { if (!res.headersSent && !res.destroyed) res.writeHead(502).end(); });
  req.on('error', () => upstream.destroy());
  if (write) req.pipe(upstream);
  else upstream.end();
}

const directPanel = process.env.NOD_INGRESS_CHAT === 'true';
const key = directPanel ? readFileSync(0, 'utf8').trimEnd() : '';
if (directPanel && !/^[A-Za-z0-9_-]{43,}$/.test(key)) throw Error('Missing internal Nod credential');
const backendCookie = 'nod-access-4310=' + key;
const upstreamHost = new URL(process.env.NOD_UPSTREAM_ORIGIN || 'http://localhost:4310').host;
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
const page = embed && !directPanel
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
  if (directPanel && !supervisorAdmin(req)) {
    res.writeHead(403).end('Home Assistant administrator session required');
    return;
  }
  if (directPanel && (chatReads.has(req.url.split('?')[0]) || chatWrites.has(req.url.split('?')[0]))) {
    serveChat(req, res);
    return;
  }
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.writeHead(405, {Allow: 'GET, HEAD'}).end();
    return;
  }
  if (directPanel && isPanelRead(req.url)) {
    if (req.url === '/') {
      res.setHeader('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'none'");
    }
    servePanelRead(req, res);
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
