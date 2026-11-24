import {readFileSync} from 'node:fs';
import {createNodRelay,privateNetwork} from './https-relay.mjs';
const root='/run/nod-relay';
const {origin,cidr}=JSON.parse(readFileSync(root+'/settings.json','utf8'));
const server=createNodRelay({
  key:readFileSync(root+'/key.pem'),cert:readFileSync(root+'/cert.pem'),origin,
  allowPeer:privateNetwork(cidr)
});
server.listen(8443,'0.0.0.0',()=>console.log('NOD_NATIVE_HTTPS_RELAY_LISTENING'));
