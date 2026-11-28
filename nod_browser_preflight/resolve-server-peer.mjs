// Startup-only resolution of the configured HA server peer.
import {lookup} from 'node:dns/promises';
import {isIPv4} from 'node:net';
import {setTimeout as delay} from 'node:timers/promises';

export async function resolveServerPeer(host, {
  resolve = lookup, sleep = delay, attempts = 30, intervalMs = 2000,
  lookupTimeoutMs = 3000,
} = {}) {
  if(typeof host !== 'string' || !/^[a-z0-9-]+-nod-native-preflight$/.test(host)) throw Error('Invalid server hostname');
  for(let attempt = 1; attempt <= attempts; attempt++) {
    let timer;
    let peers;
    try {
      peers = await Promise.race([
        resolve(host, {all:true, family:4}),
        new Promise((_,reject) => {
          timer = setTimeout(() => reject(Object.assign(Error('DNS timeout'),{code:'EAI_AGAIN'})), lookupTimeoutMs);
        }),
      ]);
    } catch (error) {
      if(!['ENOTFOUND','EAI_AGAIN'].includes(error?.code) || attempt === attempts) throw error;
      await sleep(intervalMs);
      continue;
    } finally {
      clearTimeout(timer);
    }
    // Fail closed on ambiguous or non-private answers. Never broaden the firewall.
    if(!Array.isArray(peers) || peers.length !== 1) throw Error('Ambiguous server peer');
    const peer = peers[0].address;
    if(!isIPv4(peer) || !/^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)/.test(peer)) throw Error('Non-private server peer');
    return peer;
  }
  throw Error('Server peer unavailable');
}
