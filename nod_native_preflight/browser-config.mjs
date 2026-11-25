// Root-only startup, optional browser. Never log or export PSK.
import {readFileSync,mkdirSync,chownSync,writeFileSync,chmodSync,lstatSync} from 'node:fs';
import {parsePsk} from './browser-transport.mjs';
try{
  let options={};
  try{
    const stat=lstatSync('/data/options.json');
    if(!stat.isFile()||stat.nlink!==1)throw Error();
    options=JSON.parse(readFileSync('/data/options.json','utf8'));
  }catch(e){if(e.code!=='ENOENT')throw e;}
  if(options.browser_enabled!==true){
    if(options.browser_enabled!==undefined&&options.browser_enabled!==false)throw Error();
    process.exit(0);
  }
  parsePsk(options.browser_key);
  const host=options.browser_host;
  if(typeof host!=='string'||!/^[a-z0-9-]+-nod-browser-preflight$/.test(host))throw Error();
  const dir='/run/nod-browser-client';
  mkdirSync(dir,{mode:0o700});
  const file=dir+'/settings.json';
  writeFileSync(file,JSON.stringify({psk:options.browser_key,host}),{mode:0o600,flag:'wx'});
  chownSync(file,1000,1000);
  chmodSync(file,0o400);
  chownSync(dir,1000,1000);
  chmodSync(dir,0o500);
  console.log('1');
}catch{
  console.error('NOD_BROWSER_CLIENT_DISABLED: invalid optional browser configuration');
  // Optional browser failure must not prevent the server or existing MCPs.
  process.exitCode=1;
}
