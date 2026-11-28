// Real compiled chat in Chromium; emulate Supervisor path stripping, with a
// synthetic message and the actual authenticated file created by the CI workflow.
import assert from 'node:assert/strict';
import {chromium} from '/test/node_modules/playwright/index.mjs';
const base='http://nod-ingress:8099';
const prefix='/api/hassio_ingress/synthetic';
const id=process.env.ARTIFACT_ID;
assert.match(id,/^[a-f0-9-]{36}$/);
const path='/api/artifacts/'+id;
const admin={'x-remote-user-id':'ci-admin','x-remote-user-groups':'system-admin'};
const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
try {
  const page=await browser.newPage({extraHTTPHeaders:admin});
  const message={id:'a126ecb1-52d3-470d-84a4-72e974f3e8b3',role:'assistant',
    text:'[CI Markdown artifact]('+path+')\n\n[CI absolute artifact]('+base+path+')\n\n[CI external link](https://example.com/)',turnId:null,createdAt:new Date().toISOString(),attachments:[]};
  await page.route(base+prefix+'/**',async route=>{
    const url=new URL(route.request().url());
    const target=url.pathname.slice(prefix.length)+url.search;
    if(target.startsWith('/api/events?')){
      return route.fulfill({status:200,contentType:'text/event-stream',body:'data: {"type":"refresh"}\n\n'});
    }
    const response=await route.fetch({url:base+target,headers:{...route.request().headers(),...admin}});
    if(response.ok()&&target==='/api/session'){
      const json=await response.json();
      return route.fulfill({response,json:{...json,settings:{...json.settings,onboardingCompleted:true}}});
    }
    if(response.ok()&&target==='/api/state'){
      const json=await response.json();
      return route.fulfill({response,json:{...json,messages:[message],turns:[],activity:[],hasEarlierMessages:false,hiddenMessageCount:0,hiddenMessageIds:[],pendingAnswerChoiceMessageIds:[],chatRecovery:undefined}});
    }
    await route.fulfill({response});
  });
  await page.goto(base+prefix+'/');
  const link=page.getByRole('link',{name:'CI Markdown artifact',exact:true});
  await link.waitFor({timeout:30000});
  assert.equal(await link.getAttribute('href'),prefix+path);
  assert.equal(await page.getByRole('link',{name:'CI absolute artifact',exact:true}).getAttribute('href'),prefix+path);
  assert.equal(await page.getByRole('link',{name:'CI external link',exact:true}).getAttribute('href'),'https://example.com/');
  // Fetch the rendered href through the same emulated Ingress prefix, not a
  // separately calculated URL. The bytes are from the actual Nod artifact.
  const result=await link.evaluate(async el=>{
    const response=await fetch(el.href);
    return {status:response.status,body:await response.text()};
  });
  assert.deepEqual(result,{status:200,body:'# Nod artifact CI\n'});
  console.log('NOD_INGRESS_MESSAGE_ARTIFACT_LINK_OK');
}finally{await browser.close();}
