// CI-only: run a TLS client from a separate container on the private network.
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
import {connectGateway} from './transport.mjs';
import {readFileSync} from 'node:fs';
const {psk,host}=JSON.parse(readFileSync('/test-config/client.json','utf8'));
const namespace='sk-'+'b'.repeat(24),threadId='remote-browser-ci';
function call(method,extra={}){
  return new Promise((resolve,reject)=>{
    const id=randomUUID(),socket=connectGateway({psk,host});
    let data='',settled=false;
    const timer=setTimeout(()=>finish(Error('Remote worker timeout')),90000);
    function finish(error,result){
      if(settled)return;
      settled=true;clearTimeout(timer);socket.destroy();
      error?reject(error):resolve(result);
    }
    socket.on('error',finish);
    socket.on('secureConnect',()=>socket.write(JSON.stringify({type:'request',request:{id,namespace,method,...extra}})+'\n'));
    socket.on('data',chunk=>{
      data+=chunk.toString();
      if(data.length>18*1024*1024)return finish(Error('Response exceeds limit'));
      if(!data.includes('\n'))return;
      try{const frame=JSON.parse(data.split('\n')[0]);assert.equal(frame.id,id);finish(null,frame);}catch(e){finish(e);}
    });
    socket.on('end',()=>finish(Error('Remote socket closed prematurely')));
  });
}
try{
  assert.equal((await call('act',{threadId,input:{action:'open',url:'http://93.184.216.34/'}})).ok,true);
  const snapshot=await call('act',{threadId,input:{action:'snapshot'}});
  assert.equal(snapshot.ok,true);
  assert.match(JSON.stringify(snapshot.result),/Nod browser CI fixture/);
  const screenshot=await call('screenshot',{threadId});
  assert.equal(screenshot.ok,true);
  assert.ok(screenshot.result.length>1000);
  console.log('NOD_BROWSER_CROSS_CONTAINER_TLS_OK');
}finally{
  assert.equal((await call('dispose')).ok,true);
}
