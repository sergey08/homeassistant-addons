import assert from 'node:assert/strict';
import {chromium} from '/test/node_modules/playwright/index.mjs';
import {createRequestUuid} from './request-uuid.mjs';

const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
try {
  const page=await browser.newPage({extraHTTPHeaders:{
    'x-remote-user-id':'ci-admin','x-remote-user-groups':'system-admin',
  }});
  const response=await page.goto('http://nod-ingress:8099/');
  assert.equal(response.status(),200);
  const capabilities=await page.evaluate(()=>({
    secure:window.isSecureContext, native:typeof crypto.randomUUID, rng:typeof crypto.getRandomValues,
  }));
  assert.deepEqual(capabilities,{secure:false,native:'undefined',rng:'function'});
  // Exercise the same implementation in the actual insecure browser context.
  const values=await page.evaluate('(()=>{const uuid='+createRequestUuid.toString()+';return Array.from({length:1000},()=>uuid())})()');
  assert.equal(new Set(values).size,1000);
  assert.ok(values.every(value=>/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(value)));
  console.log('NOD_HTTP_UUID_CRYPTO_OK');
} finally { await browser.close(); }
