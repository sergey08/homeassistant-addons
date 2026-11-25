// Build-time extraction from the immutable upstream source; no runtime code upload.
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import vm from 'node:vm';
const [source,destination]=process.argv.slice(2);
const code=readFileSync(resolve(source,'src/providers/docker/command.ts'),'utf8');
const definitions=readFileSync(resolve(source,'src/shared/app-definitions.ts'),'utf8');
function constant(name){
  const marker='const '+name+' = ';
  const start=code.indexOf(marker);
  if(start<0||code.indexOf(marker,start+1)>=0)throw Error('Upstream extraction anchor changed');
  const end=code.indexOf('\n`;',start);
  if(end<0)throw Error('Upstream extraction terminator changed');
  return code.slice(start+marker.length,end+2);
}
const max=definitions.match(/export const appEnvironmentNameMaxLength = (\d+);/);
const pattern=definitions.match(/export const appEnvironmentNamePattern =\s*(\/[^\n]+\/);/);
if(!max||!pattern)throw Error('Upstream environment contract changed');
const context={appEnvironmentNameMaxLength:Number(max[1]),appEnvironmentNamePattern:vm.runInNewContext(pattern[1]),JSON};
context.cliInstallProgram=vm.runInNewContext(constant('cliInstallProgram'),context,{timeout:1000});
const command=vm.runInNewContext(constant('workspaceCommandProgram'),context,{timeout:1000});
const stop=vm.runInNewContext(constant('commandStopProgram'),context,{timeout:1000});
mkdirSync(destination,{recursive:true});
writeFileSync(resolve(destination,'command.py'),command,{mode:0o444});
writeFileSync(resolve(destination,'stop.py'),stop,{mode:0o444});
writeFileSync(resolve(destination,'manifest.json'),JSON.stringify({command:createHash('sha256').update(command).digest('hex'),stop:createHash('sha256').update(stop).digest('hex')}),{mode:0o444});
console.log('NOD_WORKSPACE_UPSTREAM_PROGRAMS_EXTRACTED');
