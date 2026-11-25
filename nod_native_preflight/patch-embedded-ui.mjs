// Applied only to the pinned upstream source before Vite compilation.
import {readFileSync,writeFileSync} from 'node:fs';
const path='/app/src/web/lib/api.ts';
const source=readFileSync(path,'utf8');
const anchor='  const headers = new Headers(options.headers);';
if (source.split(anchor).length !== 2) throw Error('Unexpected upstream API implementation');
const patched=source.replace(anchor, anchor + '\n  // Independent, partitioned login for the explicitly enabled HA panel.\n  if (typeof window !== "undefined" && window.self !== window.top) {\n    headers.set("X-Nod-Embedded", "1");\n  }');
writeFileSync(path,patched);
