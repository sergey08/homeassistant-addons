import assert from 'node:assert/strict';
import {request as httpRequest} from 'node:http';
import {readFileSync} from 'node:fs';

const [, token] = readFileSync('/data/nod-native-v1/secrets', 'utf8').split('\n');
assert.match(token, /^[a-f0-9]{64}$/);
const origin = 'http://localhost:4310';
// Use raw HTTP rather than fetch: the latter may normalize Host to the URL authority.
const request = (path, options = {}) => new Promise((resolve, reject) => {
  const req = httpRequest({
    hostname: '127.0.0.1', port: 4310, path,
    method: options.method || 'GET',
    headers: {host:'localhost:4310', ...options.headers},
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
assert.equal((await request('/api/session',{headers:{cookie:cookie.split(';')[0]}})).status,200);
console.log('NOD_NATIVE_ORIGINAL_WEB_AUTH_OK');
