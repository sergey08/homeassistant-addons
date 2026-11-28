// Bounded read-only startup probe. No model, workspace, real profiles or secrets in logs.
import {readFileSync} from 'node:fs';
import {lookup} from 'node:dns/promises';
import {randomUUID} from 'node:crypto';
import {setTimeout as delay} from 'node:timers/promises';
import {connectGateway} from './browser-transport.mjs';
import {createContainerBrowserComputer} from './src/providers/container-browser/index.ts';
let phase='CONFIG';
const deadline=setTimeout(()=>{console.log('NOD_BROWSER_DIAGNOSTIC_FAILED '+phase+'_TIMEOUT');process.exit(1)},75000);
let browser;
try{
  const config=JSON.parse(readFileSync('/run/nod-browser-client/settings.json','utf8'));
  phase='INTERNAL_DNS';
  const addresses=await lookup(config.host,{all:true,family:4});
  if(addresses.length!==1)throw Error();
  console.log('NOD_BROWSER_DIAGNOSTIC_INTERNAL_DNS_OK');
  phase='TLS';
  await new Promise((resolve,reject)=>{
    const socket=connectGateway(config);
    socket.once('secureConnect',()=>{
      if(socket.getProtocol()!=='TLSv1.2'||socket.getCipher()?.name!=='ECDHE-PSK-CHACHA20-POLY1305'){socket.destroy();return reject(Error());}
      socket.end();resolve();
    });
    socket.once('error',reject);
    socket.once('close',()=>reject(Error()));
  });
  console.log('NOD_BROWSER_DIAGNOSTIC_TLS_OK');
  // A fresh namespace is deliberate: never dispose any real user browser.
  browser=createContainerBrowserComputer({dataRoot:'/tmp/nod-browser-diagnostic-'+randomUUID(),container:'nod-browser-unavailable',timeoutMs:15000,drainTimeoutMs:3000});
  phase='PUBLIC_NAVIGATION';
  const url='https://example.com/';
  const initial=await browser.act('diagnostic',{action:'open',url});
  console.log('NOD_BROWSER_DIAGNOSTIC_OPEN_RETURNED');
  function report(label,observation){
    const actual=String(observation?.url??'');
    const expected=actual===url||actual==='https://example.com';
    const text=String(observation?.text??'');
    const marker=/example domain/i.test(text);
    const blocked=/chrome-error|ERR_|not loaded|cannot be reached|navigation failed|unavailable/i.test(actual+' '+text);
    console.log('NOD_BROWSER_DIAGNOSTIC_'+label+' '+JSON.stringify({expectedUrl:expected,aboutBlank:actual==='about:blank',textLength:text.length,expectedText:marker,errorMarker:blocked}));
    return expected&&marker&&!blocked;
  }
  let matched=report('OPEN',initial);
  phase='SNAPSHOT';
  for(let attempt=1;attempt<=3&&!matched;attempt++){
    await delay(1200);
    const snapshot=await browser.act('diagnostic',{action:'snapshot'});
    matched=report('SNAPSHOT_'+attempt,snapshot);
  }
  phase='CURRENT_PAGE';
  try{
    const page=await browser.currentPage('diagnostic');
    console.log('NOD_BROWSER_DIAGNOSTIC_CURRENT_PAGE '+JSON.stringify({expectedOrigin:page.origin==='https://example.com',expectedUrl:page.url===url}));
  }catch{console.log('NOD_BROWSER_DIAGNOSTIC_CURRENT_PAGE_FAILED');}
  phase='SCREENSHOT';
  try{
    const image=await browser.screenshot('diagnostic');
    console.log('NOD_BROWSER_DIAGNOSTIC_SCREENSHOT '+JSON.stringify({available:!!image?.length,bytes:image?.length??0}));
  }catch{console.log('NOD_BROWSER_DIAGNOSTIC_SCREENSHOT_FAILED');}
  phase='CONTENT';
  if(!matched)throw Error();
  console.log('NOD_BROWSER_DIAGNOSTIC_PUBLIC_NAVIGATION_OK');
}catch{
  console.log('NOD_BROWSER_DIAGNOSTIC_FAILED '+phase);
  process.exitCode=1;
}finally{
  if(browser){
    phase='CLEANUP';
    try{await browser.dispose();}catch{console.log('NOD_BROWSER_DIAGNOSTIC_CLEANUP_FAILED');}
  }
  clearTimeout(deadline);
}
