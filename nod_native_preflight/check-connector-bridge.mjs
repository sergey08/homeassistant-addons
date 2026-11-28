import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {generateKeyPairSync} from 'node:crypto';
import Fastify from 'fastify';
import {registerLocalAccess} from './src/server/access.ts';
import {createHostedIntegrationBrowser} from './src/server/integration-browser-hosted.ts';
import {connectorNavigationUrl} from './src/web/lib/connector-navigation.js';

const local='http://localhost:4310';
const origin='https://ha.test:8123';
const broker='https://broker.test';
const key='a'.repeat(64);
const id='b'.repeat(43);
if(process.argv[2]==='serve'){
  const app=Fastify({logger:false});
  registerLocalAccess(app,4310,{key,origin:local,bearer:true});
  const hosted=createHostedIntegrationBrowser(local);
  hosted.registerRoutes(app);
  const url=await hosted.open(id,broker,async(browserKey,uiOrigin)=>{
    assert.equal(uiOrigin,origin);
    assert.equal(browserKey.kty,'EC');
    assert.equal(browserKey.crv,'P-256');
    console.log('NOD_CONNECTOR_PROOF_ORIGIN_OK');
    return broker+'/v2/connect/pair?ticket=synthetic';
  });
  await app.listen({host:'127.0.0.1',port:4310});
  const ingress=spawn(process.execPath,['/app/ingress.mjs'],{
    env:{...process.env,NOD_INGRESS_CHAT:'true',NOD_UPSTREAM_ORIGIN:local},
    stdio:['pipe','inherit','inherit'],
  });
  ingress.stdin.end(key+'\n');
  ingress.once('exit',code=>process.exit(code??1));
  console.log('NOD_CONNECTOR_FIXTURE_PATH '+new URL(url).pathname);
}else{
  const path=process.env.CONNECTOR_PATH;
  assert.match(path,/^\/api\/apps\/connect\/[A-Za-z0-9_-]{43}$/);
  const base='http://nod-connector-fixture:8099';
  const admin={'x-remote-user-id':'ci-admin','x-remote-user-groups':'system-admin'};
  assert.equal(connectorNavigationUrl(local+path,'/api/hassio_ingress/synthetic/',origin),origin+'/api/hassio_ingress/synthetic'+path);
  assert.equal(connectorNavigationUrl(local+path,'/apps',local),local+path);
  assert.equal(connectorNavigationUrl(broker+'/v2/connect/pair?ticket=x','/api/hassio_ingress/synthetic/',origin),broker+'/v2/connect/pair?ticket=x');
  assert.equal((await fetch(base+path)).status,403);
  assert.equal((await fetch(base+path,{headers:{...admin,'x-remote-user-groups':'system-users'}})).status,403);
  assert.equal((await fetch(base+'/api/apps/connect/bad',{headers:admin})).status,404);
  assert.equal((await fetch(base+'/api/apps/connect/'+'z'.repeat(43),{headers:admin})).status,403);
  assert.equal((await fetch(base+path,{method:'PUT',headers:admin})).status,405);
  const consent=await fetch(base+path,{headers:admin});
  assert.equal(consent.status,200);
  assert.match(consent.headers.get('content-security-policy'),/script-src 'nonce-/);
  assert.match(consent.headers.get('content-security-policy'),/frame-ancestors 'none'/);
  const body=await consent.text();
  assert.match(body,/Continue to sign in/);
  const secret=body.match(/"bridgeKey":"([A-Za-z0-9_-]{43})"/)?.[1];
  assert.ok(secret);
  const publicKey=generateKeyPairSync('ec',{namedCurve:'prime256v1'}).publicKey.export({format:'jwk'});
  const data=JSON.stringify({browserKey:publicKey});
  const headers={...admin,origin,'sec-fetch-site':'same-origin','x-nod-bridge':secret,'content-type':'application/json'};
  const post=overrides=>fetch(base+path,{method:'POST',headers:{...headers,...overrides},body:data});
  assert.equal((await post({origin:'http://ha.test:8123'})).status,403);
  assert.equal((await post({'sec-fetch-site':'cross-site'})).status,403);
  assert.equal((await post({'x-nod-bridge':'c'.repeat(43)})).status,403);
  assert.equal((await post({'x-remote-user-id':''})).status,403);
  const start=await post({'x-nod-ha-bridge-origin':'https://untrusted.test'});
  assert.equal(start.status,200);
  const result=await start.json();
  assert.equal(result.id,id);
  assert.equal(result.url,broker+'/v2/connect/pair?ticket=synthetic');
  assert.equal((await post({})).status,403);
  console.log('NOD_INGRESS_CONNECTOR_BRIDGE_OK');
}
