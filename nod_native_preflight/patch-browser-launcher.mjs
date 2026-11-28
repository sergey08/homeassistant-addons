// Keep upstream's lifecycle and protocol implementation, replacing only its launcher.
import {readFileSync,writeFileSync} from 'node:fs';
const file='/app/src/providers/container-browser/index.ts';
let source=readFileSync(file,'utf8');
const anchor='  const launch = options.spawn ?? spawn;';
if(source.split(anchor).length!==2)throw Error('Nod browser launcher patch anchor changed');
source=source.replace(anchor,()=>`  const launch: BrowserBridgeLauncher = options.spawn ?? (process.env.NOD_HA_BROWSER_REMOTE === '1'
    ? (_command, _args, opts) => spawn('/usr/local/bin/node', ['/app/browser-transport.mjs', 'client', '/run/nod-browser-client/settings.json'], {
        ...opts,
        env: { PATH: '/usr/local/bin:/usr/bin:/bin', HOME: '/home/node' },
        shell: false,
      })
    : spawn);`);
writeFileSync(file,source);
console.log('NOD_HA_BROWSER_LAUNCHER_PATCH_OK');
