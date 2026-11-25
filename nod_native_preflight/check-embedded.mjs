// Real Chromium, synthetic credentials, distinct TLS sites and a nested HA-like panel.
import assert from 'node:assert/strict';
import {createServer} from 'node:https';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {once} from 'node:events';
const require=createRequire('/test/node_modules/playwright/package.json');
const {chromium}=require('playwright');
const nod='https://nod.test:8443', ha='https://ha.test:9443', evil='https://evil.test:9443';
const token='x'.repeat(64);
const fixture=createServer({
  key:readFileSync('/cert/nod-privkey.pem'),cert:readFileSync('/cert/nod-fullchain.pem')
},async(req,res)=>{
  try {
    if(req.url==='/ingress' && req.headers.host==='ha.test:9443'){
      const upstream=await fetch('http://nod-ingress:8099/');
      assert.equal(upstream.status,200);
      const body=await upstream.text();
      assert.ok(body.includes(nod));
      assert.ok(!body.includes(token));
      res.writeHead(200,{'Content-Type':'text/html','Content-Security-Policy':upstream.headers.get('content-security-policy')});
      res.end(body);return;
    }
    const src=req.headers.host==='ha.test:9443'?'/ingress':nod+'/';
    res.writeHead(200,{'Content-Type':'text/html'});
    res.end('<!doctype html><iframe id="outer" sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox allow-downloads" src="'+src+'"></iframe>');
  } catch {res.writeHead(502);res.end('Fixture failed');}
});
fixture.listen(9443,'127.0.0.1');await once(fixture,'listening');
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--host-resolver-rules=MAP ha.test 127.0.0.1, MAP evil.test 127.0.0.1, MAP nod.test '+process.env.NOD_TEST_IP]});
try {
  // Only the CI synthetic certificate is untrusted. Never use this in the deployed app.
  const context=await browser.newContext({ignoreHTTPSErrors:true});
  const page=await context.newPage();
  await page.goto(ha);
  const cdp=await context.newCDPSession(page);
  await cdp.send('Network.enable');
  await cdp.send('Network.setCookieControls',{enableThirdPartyCookieRestriction:true,disableThirdPartyCookieMetadata:true,disableThirdPartyCookieHeuristics:true});
  await page.reload();
  const embedded=page.frameLocator('#outer').frameLocator('iframe[title="Nod"]');
  await embedded.locator('input[name="token"]').waitFor({timeout:30000});
  await embedded.locator('input[name="token"]').fill('wrong-token');
  await embedded.getByRole('button',{name:'Connect',exact:true}).click();
  await embedded.getByText('Check your token and try again.').waitFor({timeout:10000});
  await embedded.locator('input[name="token"]').fill(token);
  const access=page.waitForResponse(r=>r.url()===nod+'/api/access'&&r.status()===204);
  const logged=page.waitForResponse(r=>r.url()===nod+'/api/session'&&r.status()===200);
  await embedded.getByRole('button',{name:'Connect',exact:true}).click();
  const login=await access;
  const setCookie=await login.headerValue('set-cookie');
  assert.ok(setCookie?.startsWith('__Host-nod-embedded-4310='),'Expected dedicated frame cookie');
  assert.match(setCookie,/; HttpOnly; SameSite=None; Max-Age=34560000; Secure; Partitioned$/);
  await logged;
  const inner=page.frames().find(f=>f.url().startsWith(nod));
  assert.ok(inner);
  const session=await inner.evaluate(async()=>{const r=await fetch('/api/session',{headers:{'X-Nod-Embedded':'1'}});return {status:r.status,body:await r.json()}});
  assert.equal(session.status,200);
  assert.equal(typeof session.body.capabilities.developer,'boolean');
  // Playwright supplies the actual incognito browserContextId to Storage.getCookies.
  // Calling Storage.getCookies on the page CDP session can inspect the default context instead.
  const cookies=await context.cookies();
  const metadata=items=>items.map(({name,domain,httpOnly,secure,sameSite,partitionKey})=>({name,domain,httpOnly,secure,sameSite,partitionKey}));
  console.log('Embedded cookie metadata:',JSON.stringify(metadata(cookies)));
  const cookie=cookies.find(c=>c.name==='__Host-nod-embedded-4310');
  assert.ok(cookie,'Partitioned authentication cookie is present in this browser context');
  assert.equal(cookie.httpOnly,true);
  assert.equal(cookie.secure,true);
  assert.equal(cookie.sameSite,'None');
  assert.equal(cookie.partitionKey,'https://ha.test');
  assert.ok(!cookies.some(c=>c.name==='nod-access-4310'));
  assert.ok(!(await inner.evaluate(()=>document.cookie)).includes(token));
  const unmarked=await inner.evaluate(async()=> (await fetch('/api/session')).status);
  assert.equal(unmarked,401);
  const reload=page.waitForResponse(r=>r.url()===nod+'/api/session'&&r.status()===200);
  await inner.evaluate(()=>location.reload());
  await reload;
  // Verify another top-level site cannot embed or use the authorized frame session.
  const outsider=await context.newPage();
  await outsider.goto(evil);
  await outsider.waitForLoadState('networkidle');
  assert.ok(!outsider.frames().some(f=>f.url().startsWith(nod)));
  // Standalone keeps its separate strict cookie and its independent login.
  const standalone=await context.newPage();
  await standalone.goto(nod);
  await standalone.locator('input[name="token"]').waitFor({timeout:30000});
  await standalone.locator('input[name="token"]').fill(token);
  const standaloneLogin=standalone.waitForResponse(r=>r.url()===nod+'/api/session'&&r.status()===200);
  await standalone.getByRole('button',{name:'Connect',exact:true}).click();
  await standaloneLogin;
  const all=await context.cookies();
  console.log('Independent cookie metadata:',JSON.stringify(metadata(all)));
  const original=all.find(c=>c.name==='nod-access-4310');
  assert.ok(original?.httpOnly&&original.secure&&original.sameSite==='Strict'&&!original.partitionKey);
  assert.ok(all.some(c=>c.name==='__Host-nod-embedded-4310'&&c.partitionKey==='https://ha.test'));
  console.log('NOD_NATIVE_EMBEDDED_CHROMIUM_OK');
} finally {await browser.close();await new Promise(resolve=>fixture.close(resolve));}
