// Exact upstream anchors. Refuse to build if a future Nod release changes them.
import {readFileSync,writeFileSync} from 'node:fs';
const file='/app/src/providers/container-browser/worker.ts';
let source=readFileSync(file,'utf8');
function replaceOnce(before,after){
  if(source.split(before).length!==2)throw Error('Nod worker socket patch anchor changed');
  source=source.replace(before,()=>after);
}
replaceOnce("await chmod(dirname(path), 0o700);","await chmod(dirname(path), 0o750);");
replaceOnce("await chmod(path, 0o600);","await chmod(path, 0o660);");
replaceOnce("const worker = await startContainerBrowserWorker();","const worker = await startContainerBrowserWorker({ socketPath: '/run/nod-browser/control.sock', dataRoot: '/data/browser' });");
writeFileSync(file,source);
console.log('NOD_HA_BROWSER_SOCKET_PATCH_OK');
