// Root-only startup configuration. Output contains only the peer address.
import {readFileSync,lstatSync,chmodSync,chownSync,mkdirSync,writeFileSync} from 'node:fs';
import {lookup} from 'node:dns/promises';
import {isIPv4} from 'node:net';
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
  if(typeof host!=='string'||! /^[a-z0-9-]+-nod-native-preflight$/.test(host))throw Error();
  const peers=await lookup(host,{all:true,family:4});
  if(peers.length!==1)throw Error();
  const peer=peers[0].address;
  if(!isIPv4(peer)||! /^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)/.test(peer))throw Error();
  const dir='/run/nod-browser-gateway';
  mkdirSync(dir,{mode:0o700});
  const destination=dir+'/settings.json';
  writeFileSync(destination,JSON.stringify({psk:options.remote_key}),{mode:0o600,flag:'wx'});
  chownSync(destination,1001,1000);
  chownSync(dir,1001,1000);
  console.log(peer);
}catch{
  console.error('FAIL: invalid or unavailable browser peer configuration');
  process.exitCode=1;
}
