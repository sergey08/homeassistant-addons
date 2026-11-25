// Bounded read-only startup probe. No model, workspace, real profiles or secrets in logs.
import {readFileSync} from 'node:fs';
import {lookup} from 'node:dns/promises';
import {randomUUID} from 'node:crypto';
import {connectGateway} from './browser-transport.mjs';
import {createContainerBrowserComputer} from './src/providers/container-browser/index.ts';
let phase='CONFIG';
const deadline=setTimeout(()=>{console.log('NOD_BROWSER_DIAGNOSTIC_FAILED '+phase+'_TIMEOUT');process.exit(1)},45000);
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
  await browser.act('diagnostic',{action:'open',url:'https://example.com/'});
  phase='SNAPSHOT';
  const snapshot=await browser.act('diagnostic',{action:'snapshot'});
  if(!JSON.stringify(snapshot).includes('Example Domain'))throw Error();
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
