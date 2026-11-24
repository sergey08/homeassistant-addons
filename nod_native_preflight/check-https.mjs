import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

import {request as httpsRequest} from 'node:https';
import {createNodRelay, privateNetwork} from '/tmp/nod-https-relay.mjs';
import {mkdtempSync, rmSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {once} from 'node:events';
const dir = mkdtempSync('/tmp/nod-tls-ci-');
execFileSync('openssl', ['req','-x509','-newkey','rsa:2048','-nodes','-days','1',
  '-subj','/CN=nod.test','-addext','subjectAltName=DNS:nod.test',
  '-keyout',dir+'/key.pem','-out',dir+'/cert.pem'], {stdio:'ignore'});
const cert = readFileSync(dir+'/cert.pem');
assert.equal(privateNetwork('192.168.1.0/24')('192.168.1.99'),true);
assert.equal(privateNetwork('192.168.1.0/24')('::ffff:192.168.1.99'),true);
assert.equal(privateNetwork('192.168.1.0/24')('192.168.2.99'),false);
assert.throws(()=>privateNetwork('0.0.0.0/0'));
assert.throws(()=>privateNetwork('8.8.8.0/24'));
assert.throws(()=>privateNetwork('192.168.1.5/24'));
const proxy = createNodRelay({
  key:readFileSync(dir+'/key.pem'),cert,origin:'https://nod.test:8443',
  allowPeer: ip=>ip==='127.0.0.1'
});
proxy.listen(8443,'127.0.0.1');
await once(proxy,'listening');
try {
const [, token] = readFileSync('/data/nod-native-v1/secrets', 'utf8').split('\n');
assert.match(token, /^[a-f0-9]{64}$/);
const origin = 'https://nod.test:8443';
// Use raw HTTP rather than fetch: the latter may normalize Host to the URL authority.
const request = (path, options = {}) => new Promise((resolve, reject) => {
  const req = httpsRequest({
    hostname: '127.0.0.1', port: 8443, path, ca:cert, servername:'nod.test',
    method: options.method || 'GET',
    headers: {host:'nod.test:8443', ...options.headers},
    timeout: 10000
  }, res => {
    const chunks = [];
    res.on('data', chunk => chunks.push(chunk));
    res.on('error', reject);
    res.on('end', () => {
      const headers = new Headers();
      for (let i = 0; i < res.rawHeaders.length; i += 2)
        headers.append(res.rawHeaders[i], res.rawHeaders[i+1]);
      resolve(new Response([204, 304].includes(res.statusCode) ? null : Buffer.concat(chunks), {
        status: res.statusCode, headers
      }));
    });
  });
  req.on('timeout', () => req.destroy(new Error('HTTP test timed out')));
  req.on('error', reject);
  req.end(options.body);
});
const page = await request('/');
assert.equal(page.status,200);
assert.match(page.headers.get('content-type') || '', /text\/html/);
assert.match(page.headers.get('content-security-policy') || '', /frame-ancestors 'none'/);
const html = await page.text();
assert.match(html, /id="root"/);
const script = html.match(/<script[^>]+src="(\/assets\/[^"]+\.js)"/);
assert.ok(script, 'original compiled UI script is present');
const asset = await request(script[1]);
assert.equal(asset.status,200);
assert.match(asset.headers.get('content-type') || '', /javascript/);
await asset.arrayBuffer();
assert.equal((await request('/api/session')).status,401);
assert.equal((await request('/api/session',{headers:{host:'other.invalid',authorization:'Bearer '+token}})).status,403);
assert.equal((await request('/api/session',{headers:{origin:'https://other.invalid',authorization:'Bearer '+token}})).status,403);
const session=await request('/api/session',{headers:{authorization:'Bearer '+token}});
assert.equal(session.status,200);
assert.equal(typeof (await session.json()).capabilities.developer,'boolean');
const login=await request('/api/access',{method:'POST',headers:{origin,'content-type':'application/json'},body:JSON.stringify({key:token})});
assert.equal(login.status,204);
const cookie=login.headers.get('set-cookie') || '';
assert.match(cookie,/HttpOnly/i);
assert.match(cookie,/SameSite=Strict/i);
assert.match(cookie,/; Secure(?:;|$)/i);
assert.equal((await request('/api/session',{headers:{cookie:cookie.split(';')[0],'sec-fetch-site':'cross-site'}})).status,403);
assert.equal((await request('/api/session',{headers:{cookie:cookie.split(';')[0]}})).status,200);
assert.equal((await request('/api/webhooks/telegram',{method:'POST',headers:{authorization:'Bearer '+token}})).status,403);
assert.equal((await request('/api/session',{headers:{'x-forwarded-for':'192.168.1.99'}})).status,401);
console.log('NOD_NATIVE_HTTPS_AUTH_OK');
console.log('NOD_NATIVE_RESTRICTED_RELAY_OK');
 } finally {
  proxy.closeAllConnections();
  await new Promise(resolve=>proxy.close(resolve));
  rmSync(dir,{recursive:true,force:true});
}
