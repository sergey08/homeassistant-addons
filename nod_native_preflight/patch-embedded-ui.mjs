// Applied only to the pinned upstream source before Vite compilation.
import {readFileSync,writeFileSync} from 'node:fs';
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
const patched=source.replace(request,helper+'\n'+request).replace(anchor, anchor + '\n  if (typeof window !== "undefined" && window.self !== window.top) {\n    if (!(await nodPartitionSupported())) throw new Error("Open Nod in a separate tab: partitioned cookies are unavailable.");\n    headers.set("X-Nod-Embedded", "1");\n  }');
writeFileSync(path,patched);

const eventsPath='/app/src/web/lib/app-events.ts';
const events=readFileSync(eventsPath,'utf8');
const eventAnchor='    const events = new EventSource(`/api/events?account=${encodeURIComponent(owner)}`);';
if(events.split(eventAnchor).length!==2) throw Error('Unexpected upstream EventSource implementation');
const eventPatch='    const embedded = window.self !== window.top ? "&nod_embedded=1" : "";\n    const events = new EventSource(`/api/events?account=${encodeURIComponent(owner)}${embedded}`);';
writeFileSync(eventsPath,events.replace(eventAnchor,()=>eventPatch));
