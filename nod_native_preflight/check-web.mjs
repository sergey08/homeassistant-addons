import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const [, token] = readFileSync('/data/nod-native-v1/secrets', 'utf8').split('\n');
assert.match(token, /^[a-f0-9]{64}$/);
const origin = 'http://localhost:4310';
const request = (path, options = {}) => fetch('http://127.0.0.1:4310' + path, {
  ...options, redirect: 'manual', headers: {host:'localhost:4310', ...options.headers}
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
