// Optional Workspace runtime and synthetic diagnostics. Keys never leave private files.
import {readFileSync,mkdirSync,writeFileSync,chownSync,chmodSync,lstatSync} from 'node:fs';
import {parsePsk} from './workspace-transport.mjs';
try{
  let options={};
  try{
    const stat=lstatSync('/data/options.json');
    if(!stat.isFile()||stat.isSymbolicLink()||stat.nlink!==1)throw Error();
    options=JSON.parse(readFileSync('/data/options.json','utf8'));
  }catch(e){if(e.code!=='ENOENT')throw e;}
  for(const field of ['workspace_probe_enabled','workspace_runtime_enabled','workspace_runtime_probe_enabled']){
    if(options[field]!==undefined&&typeof options[field]!=='boolean')throw Error();
  }
  if(options.workspace_runtime_probe_enabled===true&&(options.workspace_runtime_enabled!==true||options.browser_enabled!==true))throw Error();
  if(options.workspace_probe_enabled!==true&&options.workspace_runtime_enabled!==true){
    if(options.workspace_probe_enabled!==undefined&&options.workspace_probe_enabled!==false)throw Error();
    process.exit(0);
  }
  parsePsk(options.workspace_key);
  if(options.workspace_command_probe_enabled!==undefined&&typeof options.workspace_command_probe_enabled!=='boolean')throw Error();
  if(options.workspace_key===options.browser_key||options.workspace_key===options.https_access_token)throw Error();
  const host=options.workspace_host;
  if(typeof host!=='string'||!/^[a-z0-9-]+-nod-workspace-preflight$/.test(host))throw Error();
  const dir='/run/nod-workspace-client';
  mkdirSync(dir,{mode:0o711});
  const file=dir+'/settings.json';
  writeFileSync(file,JSON.stringify({psk:options.workspace_key,host,commandProbe:options.workspace_command_probe_enabled===true,runtimeEnabled:options.workspace_runtime_enabled===true,probeEnabled:options.workspace_probe_enabled===true,runtimeProbe:options.workspace_runtime_probe_enabled===true}),{mode:0o600,flag:'wx'});
  chownSync(file,1000,1000);
  chmodSync(file,0o400);
  chmodSync(dir,0o711);
  console.log('1');
}catch{
  console.error('NOD_WORKSPACE_CLIENT_DISABLED: invalid optional diagnostic configuration');
  process.exitCode=1;
}
