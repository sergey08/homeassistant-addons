// Use explicitly permitted public DNS for the browser proxy. Never widen the
// private network firewall or change the HA host's DNS configuration.
import {readFileSync,writeFileSync} from 'node:fs';
const file='/app/src/providers/agent-browser/network.ts';
let source=readFileSync(file,'utf8');
const anchor="const systemResolver: AddressResolver = (host) => lookup(host, { all: true, verbatim: true });";
if(source.split(anchor).length!==2)throw Error('Nod browser resolver patch anchor changed');
source=source.replace(anchor,()=>`const publicDns = new dns.promises.Resolver({ timeout: 2500, tries: 2 });
publicDns.setServers(['1.1.1.1', '8.8.8.8']);
const systemResolver: AddressResolver = async (host) => {
  // This container deliberately has no IPv6 egress. Resolve IPv4 directly,
  // return every answer to upstream's public-address check, and never fall
  // back to HA's internal DNS or to a private destination.
  const answers = await publicDns.resolve4(host);
  return answers.map(address => ({ address, family: 4 }));
};`);
writeFileSync(file,source);
console.log('NOD_HA_PUBLIC_DNS_PATCH_OK');
