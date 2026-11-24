import {readFileSync,writeFileSync,mkdirSync,chmodSync,chownSync} from 'node:fs';
import {X509Certificate,createPrivateKey} from 'node:crypto';
import {isIP} from 'node:net';
import {privateNetwork} from './https-relay.mjs';
const opts=JSON.parse(readFileSync('/data/options.json','utf8'));
if(opts.https_enabled!==true) process.exit(0);
const origin=new URL(opts.https_origin);
if(origin.protocol!=='https:' || origin.origin!==opts.https_origin || !origin.port ||
  isIP(origin.hostname) || !origin.hostname.includes('.') || origin.hostname==='localhost')
  throw Error('Use a dedicated DNS hostname and explicit HTTPS port');
privateNetwork(opts.lan_cidr);
if(!/^[A-Za-z0-9_-]{43,}$/.test(opts.https_access_token || ''))
  throw Error('Set an independent random access token of at least 43 characters');
const cert=readFileSync('/config/nod-fullchain.pem'), key=readFileSync('/config/nod-privkey.pem');
const leaf=new X509Certificate(cert);
if(!leaf.checkHost(origin.hostname,{subject:'never'}) || !leaf.checkPrivateKey(createPrivateKey(key)) ||
   Date.parse(leaf.validFrom)>Date.now() || Date.parse(leaf.validTo)<=Date.now())
  throw Error('Certificate hostname, private key or validity does not match');
const gid=1001,root='/run/nod-relay';
mkdirSync(root,{recursive:true,mode:0o750});chownSync(root,0,gid);chmodSync(root,0o750);
for(const [name,data] of [['cert.pem',cert],['key.pem',key],['settings.json',JSON.stringify({origin:origin.origin,cidr:opts.lan_cidr})]]){
  const file=root+'/'+name;
  writeFileSync(file,data,{mode:0o640,flag:'wx'});chownSync(file,0,gid);
}
writeFileSync(root+'/token',opts.https_access_token,{mode:0o600,flag:'wx'});
process.stdout.write(origin.origin);
