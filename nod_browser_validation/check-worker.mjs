// Exercise the pinned upstream browser worker over its native Unix protocol.
// Only synthetic data and an isolated Docker network are used.
import assert from 'node:assert/strict';
import {connect} from 'node:net';
import {randomUUID,randomBytes} from 'node:crypto';
import {once} from 'node:events';
const namespace='sk-'+'a'.repeat(24);
const threadId='browser-ci';
const socketPath='/data/control.sock';
let gateway, psk, transport;
if(process.env.NOD_TEST_TLS==='1'){
  transport=await import('./transport.mjs');
  psk=randomBytes(32).toString('hex');
  gateway=transport.createGateway({psk,socketPath});
  gateway.listen(0,'127.0.0.1');
  await once(gateway,'listening');
}
function call(method,extra={}){
  return new Promise((resolve,reject)=>{
    const id=randomUUID();
    const socket=gateway?transport.connectGateway({psk,host:'127.0.0.1',port:gateway.address().port}):connect(socketPath);
    let buffer='';
    const timer=setTimeout(()=>{socket.destroy();reject(Error('Browser worker timeout: '+method));},90000);
    const finish=(error,result)=>{clearTimeout(timer);socket.destroy();error?reject(error):resolve(result);};
    socket.on('error',error=>finish(error));
    socket.on(gateway?'secureConnect':'connect',()=>socket.write(JSON.stringify({type:'request',request:{id,namespace,method,...extra}})+'\n'));
    socket.on('data',chunk=>{
      buffer+=chunk.toString();
      if(buffer.length>18*1024*1024)return finish(Error('Oversized browser response'));
      const end=buffer.indexOf('\n');
      if(end===-1)return;
      try{const response=JSON.parse(buffer.slice(0,end));assert.equal(response.id,id);finish(null,response);}catch(e){finish(e);}
    });
    socket.on('end',()=>finish(Error('Worker closed before returning a response')));
  });
}
try{
  const open=await call('act',{threadId,input:{action:'open',url:'http://93.184.216.34/'}});
  assert.equal(open.ok,true,'Public fixture navigation failed');
  const snap=await call('act',{threadId,input:{action:'snapshot'}});
  assert.equal(snap.ok,true);
  assert.match(JSON.stringify(snap.result),/Nod browser CI fixture/);
  const shot=await call('screenshot',{threadId});
  assert.equal(shot.ok,true);
  assert.ok(typeof shot.result==='string'&&shot.result.length>1000);
  // Browser proxy must deny a literal private destination, even on a reachable network.
  const blocked=await call('act',{threadId,input:{action:'open',url:'http://10.223.80.34/'}});
  if(blocked.ok){
    const state=await call('act',{threadId,input:{action:'snapshot'}});
    assert.doesNotMatch(JSON.stringify(state.result),/PRIVATE_FIXTURE_MUST_NOT_LOAD/);
  }
  console.log(gateway?'NOD_BROWSER_REAL_WORKER_TLS_OK':'NOD_UPSTREAM_BROWSER_WORKER_OK');
}finally{
  try{
    const closed=await call('dispose');
    assert.equal(closed.ok,true);
  }finally{
    if(gateway)await new Promise(resolve=>gateway.close(resolve));
  }
}
