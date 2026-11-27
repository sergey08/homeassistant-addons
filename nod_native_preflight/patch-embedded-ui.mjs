// Applied only to the pinned upstream source before Vite compilation.
import {readFileSync,writeFileSync} from 'node:fs';
const routeHelper = "export function nodApiPath(path: string, pathname: string): string {\n  const match = /^\\/api\\/hassio_ingress\\/[A-Za-z0-9_-]+(?=\\/|$)/.exec(pathname);\n  if (!match || !path.startsWith('/api/')) return path;\n  return match[0] + path;\n}\n";
writeFileSync('/app/src/web/lib/nod-api-path.ts', routeHelper);
const routeImport = "import { nodApiPath } from './nod-api-path';\n";
const path='/app/src/web/lib/api.ts';
const source=readFileSync(path,'utf8');
const anchor='  const headers = new Headers(options.headers);';
if (source.split(anchor).length !== 2) throw Error('Unexpected upstream API implementation');
const helper=`
// Fail closed if the browser cannot confirm support for partitioned cookies.
let nodPartitionProbe: Promise<boolean> | undefined;
function nodPartitionSupported() {
  return nodPartitionProbe ??= (async () => {
    const store = window.cookieStore;
    if (!store) return false;
    const name = '__Host-nod-partition-probe';
    try {
      await store.set({name, value:'1', path:'/', sameSite:'none', partitioned:true});
      return (await store.get(name))?.partitioned === true;
    } catch { return false; }
    finally {
      await store.delete({name, path:'/', partitioned:true}).catch(() => {});
    }
  })();
}
`;
const request='async function request<T>(';
if (source.split(request).length !== 2) throw Error('Unexpected upstream request implementation');
const patched=source.replace(request,helper+'\n'+request).replace(anchor, anchor + '\n  if (typeof window !== "undefined" && nodApiPath("/api/access", window.location.pathname) !== "/api/access") {\n    headers.set("X-Nod-Ingress-Request", "1");\n  } else if (typeof window !== "undefined" && window.self !== window.top) {\n    if (!(await nodPartitionSupported())) throw new Error("Open Nod in a separate tab: partitioned cookies are unavailable.");\n    headers.set("X-Nod-Embedded", "1");\n  }');
const fetchAnchor = 'const response = await fetch(path, {';
if (patched.split(fetchAnchor).length !== 2) throw Error('Unexpected upstream fetch implementation');
writeFileSync(path, routeImport + patched.replace(fetchAnchor, 'const response = await fetch(nodApiPath(path, window.location.pathname), {'));

const eventsPath='/app/src/web/lib/app-events.ts';
const events=readFileSync(eventsPath,'utf8');
const eventAnchor='    const events = new EventSource(`/api/events?account=${encodeURIComponent(owner)}`);';
if(events.split(eventAnchor).length!==2) throw Error('Unexpected upstream EventSource implementation');
const eventPatch='    const embedded = window.self !== window.top && nodApiPath("/api/events", window.location.pathname) === "/api/events" ? "&nod_embedded=1" : "";\n    const events = new EventSource(nodApiPath(`/api/events?account=${encodeURIComponent(owner)}${embedded}`, window.location.pathname));';
writeFileSync(eventsPath,routeImport + events.replace(eventAnchor,()=>eventPatch));

// Keep upstream route matching independent of the Supervisor mount point.
writeFileSync('/app/src/web/lib/panel-path.js', "const ingressPrefix = /^\\/api\\/hassio_ingress\\/[A-Za-z0-9_-]+(?=\\/|$)/;\nexport function appPath(path) {\n  return path.replace(ingressPrefix, '') || '/';\n}\nexport function panelPath(path, current = window.location.pathname) {\n  const prefix = current.match(ingressPrefix)?.[0] || '';\n  return path.startsWith('/') && !path.startsWith('//') && !ingressPrefix.test(path) ? prefix + path : path;\n}\n");
for (const [file, module] of [['app.tsx', './lib/panel-path.js'], ['lib/navigation.ts', './panel-path.js']]) {
  const target = '/app/src/web/' + file;
  let ui = readFileSync(target, 'utf8');
  if (!ui.includes('window.location.pathname')) throw Error('Missing Nod navigation path');
  ui = ui.replaceAll('window.location.pathname', 'appPath(window.location.pathname)');
  if (file === 'app.tsx') {
    ui = ui.replace("replaceState(null, '', next)", "replaceState(null, '', panelPath(next))")
      .replace('appPagePath(url.pathname)', 'appPagePath(appPath(url.pathname))');
  } else {
    ui = ui.replace("}, '', path)", "}, '', panelPath(path))")
      .replace(/(\n\s+)(path|current),(\n\s+\);)/g, '$1panelPath($2),$3');
  }
  writeFileSync(target, "import { appPath, panelPath } from '" + module + "';\n" + ui);
}

// Keep original Nod logo URLs under the authenticated Ingress mount.
const logoPatches = [
  [
    "components/service-logo.tsx",
    "../lib/panel-path.js",
    [
      [
        "src={source}",
        "src={panelPath(source)}"
      ]
    ]
  ],
  [
    "components/models.tsx",
    "../lib/panel-path.js",
    [
      [
        "maskImage: `url('/logos/${modelProviderLogos[provider] ?? 'server'}.svg')`",
        "maskImage: `url('${panelPath('/logos/' + (modelProviderLogos[provider] ?? 'server') + '.svg')}')`"
      ]
    ]
  ],
  [
    "pages/channels.tsx",
    "../lib/panel-path.js",
    [
      [
        "src={`/logos/${provider.id}.svg`}",
        "src={panelPath(`/logos/${provider.id}.svg`)}"
      ],
      [
        "src={`/logos/${editing}.svg`}",
        "src={panelPath(`/logos/${editing}.svg`)}"
      ],
      [
        "src=\"/logos/telegram.svg\"",
        "src={panelPath(\"/logos/telegram.svg\")}"
      ],
      [
        "src=\"/logos/whatsapp.svg\"",
        "src={panelPath(\"/logos/whatsapp.svg\")}"
      ]
    ]
  ],
  [
    "pages/credentials.tsx",
    "../lib/panel-path.js",
    [
      [
        "src={`/logos/sign-in/${provider}.svg`}",
        "src={panelPath(`/logos/sign-in/${provider}.svg`)}"
      ]
    ]
  ],
  [
    "pages/onboarding/steps/connection-preview.tsx",
    "../../../lib/panel-path.js",
    [
      [
        "`url(${src})`",
        "`url(${panelPath(src)})`"
      ]
    ]
  ]
];
for (const [file, module, replacements] of logoPatches) {
  const target = '/app/src/web/' + file;
  let ui = readFileSync(target, 'utf8');
  for (const [before, after] of replacements) {
    if (!ui.includes(before)) throw Error('Missing logo source in ' + file + ': ' + before);
    ui = ui.replaceAll(before, () => after);
  }
  writeFileSync(target, "import { panelPath } from '" + module + "';\n" + ui);
}

 // Use the same secure UUID generator for all request and UI identifiers on HTTP.
writeFileSync('/app/src/web/lib/request-uuid.mjs', readFileSync('/tmp/request-uuid.mjs'));
const uuidSites = [
  ['app.tsx', './lib/request-uuid.mjs', 1],
  ['pages/chat.tsx', '../lib/request-uuid.mjs', 2],
  ['pages/schedule.tsx', '../lib/request-uuid.mjs', 1],
  ['components/schedule-run.tsx', '../lib/request-uuid.mjs', 1],
  ['components/feedback.tsx', '../lib/request-uuid.mjs', 2],
  ['components/composer.tsx', '../lib/request-uuid.mjs', 1],
  ['components/browser-handoff.tsx', '../lib/request-uuid.mjs', 1],
  ['components/survey-card.tsx', '../lib/request-uuid.mjs', 1],
];
for (const [file, module, count] of uuidSites) {
  const target = '/app/src/web/' + file;
  const ui = readFileSync(target, 'utf8');
  if (ui.split('crypto.randomUUID()').length !== count + 1) throw Error('Unexpected UUID call sites in ' + file);
  writeFileSync(target, "import { createRequestUuid } from '" + module + "';\n" + ui.replaceAll('crypto.randomUUID()', 'createRequestUuid()'));
}

 // Keep canonical artifact IDs/URLs unchanged; prefix only at network boundaries.
const attachmentPath = '/app/src/web/lib/attachment-url.ts';
writeFileSync(attachmentPath, "import { panelPath } from './panel-path.js';\n" + readFileSync(attachmentPath, 'utf8') +
  "\nexport function artifactRequestUrl(url: string) { return ownedArtifactUrl(url) ? panelPath(url) : url; }\n");
const artifactSites = [
  ['components/file-actions.tsx', [["href={artifact.url}", "href={artifactRequestUrl(artifact.url)}"], ["new URL(artifact.url, location.origin)", "new URL(artifactRequestUrl(artifact.url), location.origin)"]]],
  ['components/attachment-data.tsx', [["href={item.downloadUrl}", "href={artifactRequestUrl(item.downloadUrl)}"], ["fetch(item.url, {", "fetch(artifactRequestUrl(item.url), {"]]],
  ['components/attachment-images.tsx', [["src={image.url}", "src={artifactRequestUrl(image.url)}"]]],
  ['components/artifact-drawer.tsx', [["src={item.url}", "src={artifactRequestUrl(item.url)}"], ["const url = link?.getAttribute('href');", "const href = link?.getAttribute('href');\n          const url = href?.replace(/^\\/api\\/hassio_ingress\\/[A-Za-z0-9_-]+(?=\\/|$)/, '');"]]],
  ['components/attachment-video.tsx', [["src={item.url}", "src={artifactRequestUrl(item.url)}"]]],
  ['components/audio-player.tsx', [["src={visible ? item.url : undefined}", "src={visible ? artifactRequestUrl(item.url) : undefined}"], ["href={item.url}", "href={artifactRequestUrl(item.url)}"]]],
  ['components/attachment-pdf.tsx', [["return pdf.getDocument({\n    url,", "return pdf.getDocument({\n    url: artifactRequestUrl(url),"]]],
];
for (const [file, replacements] of artifactSites) {
  const target = '/app/src/web/' + file;
  let ui = readFileSync(target, 'utf8');
  for (const [before, after] of replacements) {
    if (ui.split(before).length !== 2) throw Error('Unexpected artifact URL call site in ' + file);
    ui = ui.replace(before, () => after);
  }
  writeFileSync(target, "import { artifactRequestUrl } from '../lib/attachment-url';\n" + ui);
}

 // Artifact routes in the pinned upstream do not check the optional account header.
 // Match the existing account guard, while retaining direct download links without it.
const artifactServer = '/app/src/server/app.ts';
let artifactSource = readFileSync(artifactServer, 'utf8');
for (const route of ['/api/artifacts/:id/metadata', '/api/artifacts/:id']) {
  const before = "app.get<{ Params: { id: string } }>('" + route + "', async (request, reply) => {";
  if (artifactSource.split(before).length !== 2) throw Error('Unexpected artifact server route ' + route);
  artifactSource = artifactSource.replace(before, () => before +
    "\n    const expectedAccount = request.headers['x-nod-account'];\n    if (expectedAccount !== undefined && expectedAccount !== ownerId) return reply.code(401).send({ error: 'Sign in to continue.' });");
}
writeFileSync(artifactServer, artifactSource);

 // Hosted broker connection links must retain the canonical URL for hashing/polling.
 // Only navigation of the exact internally generated capability uses HA Ingress.
const connectorUrlFile = '/app/src/web/lib/connection-url.ts';
writeFileSync(connectorUrlFile, "import { panelPath } from './panel-path.js';\n" +
  readFileSync(connectorUrlFile, 'utf8') +
  "\nexport function connectorNavigationUrl(value: string) {\n  const match = /^http:\\/\\/localhost:4310(\\/api\\/apps\\/connect\\/[A-Za-z0-9_-]{43})$/.exec(value);\n  return match ? panelPath(match[1]) === match[1] ? value : panelPath(match[1]) : value;\n}\n");
const connectorSites = [
  ['pages/apps.tsx', [['popup.location.href = url;', 'popup.location.href = connectorNavigationUrl(url);']]],
  ['hooks/use-app-sign-in.ts', [['popup.location.href = url;', 'popup.location.href = connectorNavigationUrl(url);'], ["window.open(signInUrl, ", "window.open(connectorNavigationUrl(signInUrl), "]]],
  ['components/app-connection-dialog.tsx', [['href={signIn.url}', 'href={signIn.url ? connectorNavigationUrl(signIn.url) : undefined}']]],
  ['components/setup-link.tsx', [['popup.location.href = href;', 'popup.location.href = connectorNavigationUrl(href);'], ['href={href}', 'href={connectorNavigationUrl(href)}']]],
  ['components/app-discovery-dialog.tsx', [['popup.location.href = url;', 'popup.location.href = connectorNavigationUrl(url);']]],
];
for (const [file, replacements] of connectorSites) {
  const target = '/app/src/web/' + file;
  let ui = readFileSync(target, 'utf8');
  for (const [before, after] of replacements) {
    if (!ui.includes(before)) throw Error('Missing connector navigation in ' + file);
    ui = ui.replaceAll(before, () => after);
  }
  writeFileSync(target, "import { connectorNavigationUrl } from '../lib/connection-url';\n" + ui);
}

// Preserve upstream capability expiry, one-use bridge key and ECDSA challenge.
// Only the dedicated HA proxy can supply the actual HTTPS browser origin.
const hostedConnector = '/app/src/server/integration-browser-hosted.ts';
let hosted = readFileSync(hostedConnector, 'utf8');
const hostedStart = 'const remote = new URL(await attempt.start(browserKey, origin));';
if (hosted.split(hostedStart).length !== 2) throw Error('Unexpected hosted connector start');
hosted = hosted.replace(hostedStart, () =>
  "const forwarded = request.headers['x-nod-ha-bridge-origin'];\n" +
  "            let browserOrigin = origin;\n" +
  "            if (forwarded !== undefined) {\n" +
  "              if (origin !== 'http://localhost:4310' || typeof forwarded !== 'string' || forwarded.length > 512) throw new Error('Invalid HA connector origin');\n" +
  "              const parsed = new URL(forwarded);\n" +
  "              if (parsed.protocol !== 'https:' || parsed.origin !== forwarded || parsed.username || parsed.password) throw new Error('Invalid HA connector origin');\n" +
  "              browserOrigin = parsed.origin;\n" +
  "            }\n" +
  "            const remote = new URL(await attempt.start(browserKey, browserOrigin));");
const secureAnchor = "const status=document.getElementById('status');";
if (hosted.split(secureAnchor).length !== 2) throw Error('Unexpected hosted connector page');
hosted = hosted.replace(secureAnchor, () => secureAnchor +
  "\nif(!window.isSecureContext||!crypto.subtle){button.disabled=true;status.textContent='Open Home Assistant with a trusted HTTPS certificate to connect apps.';}");
writeFileSync(hostedConnector, hosted);

// The broker's callback contract uses /api/apps/callback at the loopback origin.
// Do not disclose the private HA ingress capability to the external provider.
// Offer a bounded, authenticated manual completion path using the same callback verification.
const connectorServer = '/app/src/server/integrations.ts';
let integrationSource = readFileSync(connectorServer, 'utf8');
const callbackStart = 'const callback = async (request: FastifyRequest, reply: FastifyReply) => {';
const callbackEnd = "scope.get('/api/apps/callback', callback);";
const startAt = integrationSource.indexOf(callbackStart);
const endAt = integrationSource.indexOf(callbackEnd);
if (startAt < 0 || endAt <= startAt || integrationSource.split(callbackStart).length !== 2 ||
    integrationSource.split(callbackEnd).length !== 2) throw Error('Unexpected connector callback implementation');
let callbackBody = integrationSource.slice(startAt,endAt);
callbackBody = callbackBody.replace(callbackStart,
  'const callback = async (query: unknown, reply: FastifyReply, manual = false) => {')
  .replaceAll('request.query', 'query');
const destinationAnchor = "const destination = options.callbackReturnTo ? 'desktop' : returnTo;";
if (callbackBody.split(destinationAnchor).length !== 2) throw Error('Unexpected connector callback return');
callbackBody = callbackBody.replace(destinationAnchor,
  "if (manual) return reply.header('Cache-Control', 'no-store').code(['connected','continued'].includes(outcome) ? 200 : 409).send({ outcome });\n        " + destinationAnchor);
const manualRoute = [
  "scope.get('/api/apps/callback', (request, reply) => callback(request.query, reply));",
  "      scope.post('/api/apps/setup-complete', async (request, reply) => {",
  "        if (request.headers['x-nod-account'] !== undefined && request.headers['x-nod-account'] !== configuredOwner) return reply.code(401).send({ error: 'Sign in to continue.' });",
  "        const input = z.object({ state: z.string().regex(/^[A-Za-z0-9_-]{43}$/), completion_token: z.string().min(1).max(24000), hash: z.string().regex(/^[a-f0-9]{64}$/) }).strict().parse(request.body);",
  "        const callbackHash = createHash('sha256').update(input.state).digest('hex');",
  "        const pending = await pool.query(",
  "          \"SELECT id FROM app_connections WHERE owner_id=$1 AND callback_hash=$2 AND setup_link_hash=$3 AND provider_id='composio' AND pending_account_id=$4 AND callback_verifier IS NOT NULL AND callback_expires>now() AND callback_claim_id IS NULL AND NOT revoked\",",
  "          [configuredOwner, callbackHash, input.hash, 'pending_'+input.state]);",
  "        if (!pending.rowCount) return reply.code(409).send({ error: 'This sign-in attempt is unavailable. Use the current connection window.' });",
  "        return callback({ state: input.state, completion_token: input.completion_token }, reply, true);",
  "      });",
].join('\n');
integrationSource = integrationSource.slice(0,startAt)+callbackBody+manualRoute+integrationSource.slice(endAt+callbackEnd.length);
writeFileSync(connectorServer,integrationSource);

const dialogFile = '/app/src/web/components/app-connection-dialog.tsx';
let dialog = readFileSync(dialogFile,'utf8');
const titleAnchor = '  const title = useRef<HTMLHeadingElement>(null);';
if(dialog.split(titleAnchor).length !== 2) throw Error('Unexpected connector dialog');
dialog = dialog.replace(titleAnchor, () => titleAnchor +
  "\n  const [callbackAddress,setCallbackAddress] = useState('');\n  const [callbackNotice,setCallbackNotice] = useState('');\n  const [callbackBusy,setCallbackBusy] = useState(false);\n" +
  "  const manual = Boolean(signIn?.url && connectorNavigationUrl(signIn.url) !== signIn.url && window.isSecureContext);\n" +
  "  useEffect(() => { setCallbackAddress(''); setCallbackNotice(''); setCallbackBusy(false); }, [signIn?.url]);\n" +
  "  async function completeHaConnector() {\n" +
  "    if (!signIn?.url || !manual || callbackBusy) return;\n" +
  "    setCallbackBusy(true); setCallbackNotice('');\n" +
  "    try {\n" +
  "      const address = new URL(callbackAddress.trim());\n" +
  "      const state = address.searchParams.get('state');\n" +
  "      const token = address.searchParams.get('completion_token');\n" +
  "      if (address.origin !== 'http://localhost:4310' || address.pathname !== '/api/apps/callback' || address.username || address.password || address.hash || address.searchParams.size !== 2 || !state || !/^[A-Za-z0-9_-]{43}$/.test(state) || !token || token.length > 24000) throw new Error('Invalid callback address');\n" +
  "      const hash = await setupLinkHash(signIn.url);\n" +
  "      await post('/api/apps/setup-complete', { state, completion_token: token, hash });\n" +
  "      setCallbackNotice('Authorization received. Checking the connection…');\n" +
  "    } catch { setCallbackNotice('Could not complete the current sign-in. Check the return address and try again.'); }\n" +
  "    finally { setCallbackAddress(''); setCallbackBusy(false); }\n" +
  "  }");
const actionsAnchor = '            <div className="app-connect-actions">';
if(dialog.split(actionsAnchor).length!==2)throw Error('Missing connector actions');
dialog = dialog.replace(actionsAnchor, () => 
  "            {manual && !outcome && (\n" +
  "              <div data-analytics-private style={{display:'grid',gap:8,textAlign:'left'}}>\n" +
  "                <p>After approving access, your browser may return to localhost and show a connection error. Copy the complete address from that window and paste it here. Do not share that address with anyone.</p>\n" +
  "                <label htmlFor=\"nod-ha-connector-return\">Return address</label>\n" +
  "                <input id=\"nod-ha-connector-return\" type=\"password\" autoComplete=\"off\" spellCheck={false} value={callbackAddress} maxLength={100000} onChange={(event)=>setCallbackAddress(event.target.value)} />\n" +
  "                <Button type=\"button\" disabled={callbackBusy || !callbackAddress.trim()} onClick={()=>void completeHaConnector()}>Complete sign-in</Button>\n" +
  "                {callbackNotice && <p role=\"status\">{callbackNotice}</p>}\n" +
  "              </div>\n" +
  "            )}\n" + actionsAnchor);
dialog=dialog.replace("import { useEffect, useRef, type ComponentProps } from 'react';","import { useEffect, useRef, useState, type ComponentProps } from 'react';");
dialog=dialog.replace("import { connectorNavigationUrl } from '../lib/connection-url';","import { connectorNavigationUrl, setupLinkHash } from '../lib/connection-url';\nimport { post } from '../lib/api';");
writeFileSync(dialogFile,dialog);
