// Expose only the existing browser tool when the optional HA worker is enabled.
// Keep upstream's schemas, runtime guards, trust checks and restricted modes.
import {readFileSync,writeFileSync} from 'node:fs';
const file='/app/src/providers/pi/index.ts';
let source=readFileSync(file,'utf8');
function replaceOnce(anchor,replacement){
  if(source.split(anchor).length!==2)throw Error('Nod browser exposure patch anchor changed');
  source=source.replace(anchor,()=>replacement);
}
replaceOnce("      const compactTools = [",`      const haBrowserDirect = process.env.NOD_HA_BROWSER_REMOTE === '1' &&
        !input.restricted && input.tools.some(tool => tool.name === 'browser' && !tool.deferred);
      const compactTools = [
        ...(haBrowserDirect ? ['nod_browser'] : []),`);
replaceOnce("...((!input.restricted && !tool.eager) || tool.deferred || budget.compact",
  "...(!(haBrowserDirect && tool.name === 'browser') && ((!input.restricted && !tool.eager) || tool.deferred || budget.compact)");
writeFileSync(file,source);
console.log('NOD_HA_BROWSER_EXPOSURE_PATCH_OK');
