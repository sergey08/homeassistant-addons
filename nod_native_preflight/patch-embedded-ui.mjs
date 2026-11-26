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
