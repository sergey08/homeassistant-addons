import http from 'node:http';
import { readFileSync } from 'node:fs';

import { pipeline } from 'node:stream';

// The UI bundle is served by Nod on loopback. Only generated Vite assets
// qualify here. Session, uploads and API routes use separate handlers.
function isBundleAsset(path) {
  return /^\/assets\/[A-Za-z0-9_-]+\.(?:m?js|css|woff2?|png|svg)(?:\?v=[A-Za-z0-9_-]+)?$/.test(path);
}

function isBundledLogo(path) {
  return /^\/logos\/(?:(?:models|sign-in)\/)?[A-Za-z0-9_-]+\.svg$/.test(path);
}
function isAppIcon(path) {
  return /^\/api\/apps\/(?:catalog\/)?[A-Za-z0-9_-]{1,128}\/icon$/.test(path);
}

// Artifact bodies have a dedicated read-only handler. Never route arbitrary paths.
function isArtifactRead(path) {
  return /^\/api\/artifacts\/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/.test(path);
}

function serveArtifact(req, res, port = 4310) {
  if (!['GET', 'HEAD'].includes(req.method)) {
    res.writeHead(405, {Allow: 'GET, HEAD'}).end();
    return;
  }
  const headers = {Host: upstreamHost, Cookie: backendCookie, 'Accept-Encoding': 'identity'};
  if (req.headers['x-nod-account']) headers['X-Nod-Account'] = req.headers['x-nod-account'];
  if (req.headers.range) {
    if (!/^bytes=(?:\d{1,16}-\d{0,16}|-\d{1,16})$/.test(req.headers.range)) {
      res.writeHead(416).end();
      return;
    }
    headers.Range = req.headers.range;
  }
  const upstream = http.request({
    hostname: '127.0.0.1', port, path: req.url, method: req.method, headers,
  }, reply => {
    const status = reply.statusCode;
    const type = (reply.headers['content-type'] || '').split(';')[0].trim();
    const responseHeaders = {
      'Cache-Control': 'private, no-store',
      'X-Content-Type-Options': 'nosniff',
      'Content-Security-Policy': "default-src 'none'; sandbox; frame-ancestors 'none'",
      'Cross-Origin-Resource-Policy': 'same-origin',
      'Referrer-Policy': 'no-referrer',
    };
    if (status === 416) {
      if (reply.headers['content-range']) responseHeaders['Content-Range'] = reply.headers['content-range'];
      reply.resume();
      res.writeHead(416, responseHeaders).end();
      return;
    }
    if ([400,401,403,404,409].includes(status) && type === 'application/json') {
      res.writeHead(status, {...responseHeaders, 'Content-Type':'application/json'});
      pipeline(reply, res, () => {});
      return;
    }
    // Only successful file responses with Nod's attachment disposition.
    // Preserve safe inline previews, but force everything else to download.
    const disposition = reply.headers['content-disposition'];
    const filename = typeof disposition === 'string' &&
      /^(?:inline|attachment); (filename\*=UTF-8''[^\r\n;]+)$/.exec(disposition);
    if (![200,206].includes(status) || !type || !filename) {
      reply.resume();
      res.writeHead(502, responseHeaders).end();
      return;
    }
    const inline = /^(image\/(png|jpeg|webp|gif|avif|bmp|svg\+xml)|audio\/(mpeg|wav|x-wav|webm|ogg|mp4|aac|flac)|video\/(mp4|webm|ogg)|application\/pdf)$/.test(type);
    responseHeaders['Content-Type'] = type;
    responseHeaders['Content-Disposition'] = (inline && disposition.startsWith('inline;') ? 'inline' : 'attachment') + '; ' + filename[1];
    for (const [key, name] of [['content-length','Content-Length'],['content-range','Content-Range'],['accept-ranges','Accept-Ranges']]) {
      if (reply.headers[key]) responseHeaders[name] = reply.headers[key];
    }
    res.writeHead(status, responseHeaders);
    pipeline(reply, res, () => {});
  });
  res.once('close', () => upstream.destroy());
  upstream.setTimeout(30000, () => upstream.destroy(new Error('Artifact timeout')));
  upstream.on('error', () => {
    if (!res.headersSent && !res.destroyed) res.writeHead(502).end();
    else if (!res.destroyed) res.destroy();
  });
  upstream.end();
}

// Hosted connector consent uses an expiring capability and a separate bridge key.
// Only the authenticated Supervisor admin panel can reach it through Ingress.
function isConnectorBridge(path) {
  return /^\/api\/apps\/connect\/[A-Za-z0-9_-]{43}$/.test(path);
}
function connectorHttpsOrigin(value) {
  if (typeof value !== 'string' || value.length > 512) return null;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && url.origin === value && !url.username && !url.password ? url.origin : null;
  } catch { return null; }
}
async function serveConnectorBridge(req, res, port = 4310) {
  const write = req.method === 'POST';
  if (!write && req.method !== 'GET') {
    res.writeHead(405, {Allow:'GET, POST'}).end();
    return;
  }
  const headers = {Host:upstreamHost, Cookie:backendCookie, 'Accept-Encoding':'identity'};
  let body;
  if (write) {
    // Origin and Fetch Metadata are browser-controlled; do not trust a caller's
    // custom forwarded origin. The upstream capability and bridge key still apply.
    const origin = connectorHttpsOrigin(req.headers.origin);
    if (!origin || req.headers['sec-fetch-site'] !== 'same-origin' ||
        !/^[A-Za-z0-9_-]{43}$/.test(req.headers['x-nod-bridge'] || '') ||
        req.headers['content-type']?.split(';')[0] !== 'application/json' ||
        (req.headers['content-length'] !== undefined &&
          (!/^\d{1,4}$/.test(req.headers['content-length']) || Number(req.headers['content-length']) > 4096))) {
      res.writeHead(403, {'Content-Type':'application/json'}).end(JSON.stringify({error:'Open Home Assistant using trusted HTTPS and start the sign-in again.'}));
      return;
    }
    const chunks=[];
    let size=0;
    try {
      for await (const chunk of req) {
        size+=chunk.length;
        if(size>4096){res.writeHead(413).end();return;}
        chunks.push(chunk);
      }
    } catch { if(!res.destroyed)res.writeHead(400).end();return; }
    body=Buffer.concat(chunks,size);
    Object.assign(headers, {
      Origin:upstreamOrigin, 'Sec-Fetch-Site':'same-origin',
      'X-Nod-Bridge':req.headers['x-nod-bridge'],
      'X-Nod-HA-Bridge-Origin':origin,
      'Content-Type':'application/json', 'Content-Length':body.length,
    });
  }
  const upstream = http.request({
    hostname:'127.0.0.1', port, path:req.url, method:req.method, headers,
  }, reply => {
    const type = (reply.headers['content-type'] || '').split(';')[0].trim();
    const status = reply.statusCode;
    const csp = reply.headers['content-security-policy'];
    const html = !write && status === 200 && type === 'text/html' &&
      typeof csp === 'string' && csp.includes("default-src 'none'") &&
      csp.includes("frame-ancestors 'none'") && /script-src 'nonce-[A-Za-z0-9+/=]+'/.test(csp);
    const json = type === 'application/json' && [200,400,401,403,404,409,413,429,503].includes(status);
    if (!html && !json) {
      reply.resume();
      res.writeHead(502).end();
      return;
    }
    res.writeHead(status, {
      'Content-Type':reply.headers['content-type'],
      'Cache-Control':'private, no-store', 'Referrer-Policy':'no-referrer',
      'X-Content-Type-Options':'nosniff',
      'Content-Security-Policy':html ? csp : "default-src 'none'; frame-ancestors 'none'",
    });
    pipeline(reply,res,()=>{});
  });
  res.once('close',()=>upstream.destroy());
  upstream.setTimeout(30000,()=>upstream.destroy(new Error('Connector bridge timeout')));
  upstream.on('error',()=>{
    if(!res.headersSent&&!res.destroyed)res.writeHead(502).end();
    else if(!res.destroyed)res.destroy();
  });
  upstream.end(body);
}

const uiFiles = new Set(['/', '/theme-init.js', '/favicon.svg', '/favicon.ico', '/apple-touch-icon.png']);
function isPanelRead(path) {
  return uiFiles.has(path) || isBundleAsset(path) || isBundledLogo(path) || isAppIcon(path) || path === '/api/session';
}

function servePanelRead(req, res, port = 4310) {
  if (!isPanelRead(req.url) || !['HEAD', 'GET'].includes(req.method)) {
    res.writeHead(404).end();
    return;
  }
  const upstream = http.request({
    hostname: '127.0.0.1', port, path: req.url, method: req.method,
    headers: { Host: upstreamHost, 'Accept-Encoding': 'identity',
      ...((req.url === '/api/session' || isAppIcon(req.url)) ? { Cookie: backendCookie } : {}),
    },
  }, reply => {
    const type = (reply.headers['content-type'] || '').split(';')[0].trim();
    const session = req.url === '/api/session';
    const logo = isBundledLogo(req.url);
    const icon = isAppIcon(req.url);
    const validType = req.url === '/' ? type === 'text/html' :
      session ? type === 'application/json' : logo ? type === 'image/svg+xml' :
      icon ? ['image/svg+xml', 'image/png', 'image/jpeg', 'image/webp', 'image/gif', 'image/x-icon', 'image/vnd.microsoft.icon'].includes(type) :
      type && type !== 'text/html';
    if (!validType || !(reply.statusCode === 200 || (session && reply.statusCode === 401))) {
      reply.resume();
      res.writeHead(reply.statusCode === 404 ? 404 : 502).end();
      return;
    }
    res.writeHead(reply.statusCode, {
      'Content-Type': reply.headers['content-type'],
      'X-Content-Type-Options': 'nosniff',
      'Cache-Control': 'private, no-store',
      ...((logo || icon) ? { 'Content-Security-Policy': "default-src 'none'; sandbox; frame-ancestors 'none'", 'Cross-Origin-Resource-Policy': 'same-origin' } : {}),
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
  '/api/channels', '/api/channel-settings', '/api/trust/entries', '/api/vault/activity', '/api/vault', '/api/vault/sessions']);
const chatWrites = new Set(['/api/messages', '/api/account/welcome', '/api/onboarding/profile',
  '/api/onboarding/updates-email', '/api/onboarding/suggestions', '/api/account/model-setup', '/api/account/prepare']);

// Explicit method/path pairs for the pinned upstream UI. Never proxy webhooks.
// Vault reveal operations retain upstream authorization and require the Ingress write marker.
const settingsRoutes = [
  ['POST', /^\/api\/apps\/setup-(?:status|cancel|complete)$/],
  ['GET', /^\/api\/artifacts\/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\/metadata$/],
  // Conversation search and focus: upstream checks owner, active thread and visibility.
  ['GET', /^\/api\/messages\/search$/],
  ['GET', /^\/api\/messages\/around\/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/],
  // Final onboarding save and account preferences (upstream strict schema).
  ['PATCH', /^\/api\/account$/],
  // Model sign-in uses explicit authenticated API routes; never proxy the public callback.
  ['POST', /^\/api\/models\/oauth(?:\/complete)?$/],
  ['GET', /^\/api\/models\/oauth\/status\/[A-Za-z0-9_-]{32,128}$/],
  ['DELETE', /^\/api\/models\/oauth\/[A-Za-z0-9_-]{32,128}$/],
  ['PUT', /^\/api\/models\/selection$/],
  ['POST', /^\/api\/vault(?:\/import)?$/],
  ['PATCH', /^\/api\/vault\/[0-9a-fA-F-]{36}$/],
  ['DELETE', /^\/api\/vault\/[0-9a-fA-F-]{36}$/],
  ['POST', /^\/api\/vault\/[0-9a-fA-F-]{36}\/(?:details|password|card-number)$/],
  ['DELETE', /^\/api\/vault\/sessions\/[A-Za-z0-9_-]+$/],
  ['PUT', /^\/api\/channel-settings\/(?:telegram|whatsapp)$/],
  ['DELETE', /^\/api\/channel-settings\/(?:telegram|whatsapp)$/],
  ['POST', /^\/api\/channel-settings\/(?:telegram|whatsapp)\/reconnect$/],
  ['GET', /^\/api\/tasks\/[^/]+(?:\/(?:commands|schedule-draft))?$/],
  ['POST', /^\/api\/schedules$/],
  ['POST', /^\/api\/schedules\/[^/]+\/(?:run|preview)$/],
  ['POST', /^\/api\/schedules\/[^/]+\/runs\/[^/]+\/stop$/],
  ['PATCH', /^\/api\/(?:schedules|tasks)\/[^/]+$/],
  ['PUT', /^\/api\/(?:schedules|tasks)\/[^/]+\/model$/],
  ['DELETE', /^\/api\/schedules\/[^/]+$/],
  ['POST', /^\/api\/tasks\/[^/]+\/stop$/],
  ['POST', /^\/api\/apps\/[^/]+\/connect$/],
  ['POST', /^\/api\/apps\/[^/]+\/accounts\/[^/]+\/disconnect$/],
  ['PATCH', /^\/api\/apps\/mcp\/[^/]+$/],
  ['PUT', /^\/api\/trust\/limit$/],
  ['GET', /^\/api\/trust\/entries\/[^/]+\/steps$/],
];
function settingsAllowed(method, path) {
  return !/%(?:2f|5c|2e|25)/i.test(path) && settingsRoutes.some(([verb, pattern]) => verb === method && pattern.test(path));
}

function serveChat(req, res, port = 4310) {
  const path = req.url.split('?')[0];
  const events = req.url.split('?')[0] === '/api/events';
  const write = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(req.method);
  if (!((req.method === 'GET' && chatReads.has(path)) || (req.method === 'POST' && chatWrites.has(path)) || settingsAllowed(req.method, path))) {
    res.writeHead(405).end();
    return;
  }
  if (write && (req.headers['x-nod-ingress-request'] !== '1' ||
      (req.headers['content-type'] && req.headers['content-type'].split(';')[0] !== 'application/json') ||
      (!req.headers['content-type'] && (Number(req.headers['content-length'] || 0) > 0 || req.headers['transfer-encoding'])))) {
    res.writeHead(403).end();
    return;
  }
  const headers = { Host: upstreamHost, Cookie: backendCookie };
  if (write && req.headers['content-type']) headers['Content-Type'] = 'application/json';
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
const upstreamOrigin = new URL(process.env.NOD_UPSTREAM_ORIGIN || 'http://localhost:4310').origin;
const upstreamHost = new URL(upstreamOrigin).host;
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
  if (directPanel && isConnectorBridge(req.url)) {
    void serveConnectorBridge(req,res).catch(()=>{if(!res.headersSent&&!res.destroyed)res.writeHead(502).end();else if(!res.destroyed)res.destroy();});
    return;
  }
  if (directPanel && isArtifactRead(req.url)) {
    serveArtifact(req, res);
    return;
  }
  if (directPanel && (chatReads.has(req.url.split('?')[0]) || chatWrites.has(req.url.split('?')[0]) || settingsAllowed(req.method, req.url.split('?')[0]))) {
    serveChat(req, res);
    return;
  }
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.writeHead(405, {Allow: 'GET, HEAD'}).end();
    return;
  }
  if (directPanel && isPanelRead(req.url)) {
    if (req.url === '/') {
      res.setHeader('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; worker-src 'self'; connect-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'none'");
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
