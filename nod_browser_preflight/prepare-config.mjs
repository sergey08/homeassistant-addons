// Root-only startup configuration. Output contains only the peer address.
import {readFileSync,lstatSync,chmodSync,chownSync,mkdirSync,writeFileSync} from 'node:fs';
import {resolveServerPeer} from './resolve-server-peer.mjs';
import {parsePsk} from './transport.mjs';
const file='/data/options.json';
try{
  let options={};
  try{
    const stat=lstatSync(file);
    if(!stat.isFile()||stat.isSymbolicLink()||stat.nlink!==1)throw Error();
    chownSync(file,0,0);
    chmodSync(file,0o600);
    options=JSON.parse(readFileSync(file,'utf8'));
  }catch(e){if(e.code!=='ENOENT')throw e;}
  if(options.remote_enabled!==true){
    if(options.remote_enabled!==undefined&&options.remote_enabled!==false)throw Error();
    process.exit(0);
  }
  parsePsk(options.remote_key);
  const host=options.server_host;
  const peer=await resolveServerPeer(host);
  const dir='/run/nod-browser-gateway';
  mkdirSync(dir,{mode:0o711});
  chmodSync(dir,0o711);
  const destination=dir+'/settings.json';
  writeFileSync(destination,JSON.stringify({psk:options.remote_key}),{mode:0o600,flag:'wx'});
  chownSync(destination,1001,1000);
  chmodSync(destination,0o400);
  console.log(peer);
}catch{
  console.error('FAIL: invalid or unavailable browser peer configuration');
  process.exitCode=1;
}
