import assert from 'node:assert/strict';
import net from 'node:net';
import tls from 'node:tls';
import {randomBytes} from 'node:crypto';
import {mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {once} from 'node:events';
import {PassThrough} from 'node:stream';
import {createGateway,connectGateway,runClient,parsePsk} from './transport.mjs';
const psk=randomBytes(32).toString('hex');
const directory=await mkdtemp(join(tmpdir(),'nod-transport-'));
const socketPath=join(directory,'worker.sock');
let accepted=0;
const peers=new Set();
const fixture=net.createServer(socket=>{
  accepted++;
  peers.add(socket);
  socket.on('close',()=>peers.delete(socket));
  socket.on('error',()=>socket.destroy());
  socket.on('data',data=>socket.end(Buffer.concat([Buffer.from('worker:'),data])));
});
const gateway=createGateway({psk,socketPath});
function failed(socket){
  return new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>{socket.destroy();reject(Error('Rejected connection did not close'));},8000);
    socket.on('error',()=>{});
    socket.on('close',()=>{clearTimeout(timer);resolve();});
  });
}
try{
  assert.throws(()=>parsePsk(''));
  assert.throws(()=>parsePsk('0'.repeat(64)));
  fixture.listen(socketPath);
  await once(fixture,'listening');
  gateway.listen(0,'127.0.0.1');
  await once(gateway,'listening');
  const host='127.0.0.1',port=gateway.address().port;
  const wrong=connectGateway({psk:randomBytes(32).toString('hex'),host,port});
  await failed(wrong);
  const raw=net.connect(port,host);
  raw.on('connect',()=>raw.write('plaintext\n'));
  await failed(raw);
  const certless=tls.connect({host,port,rejectUnauthorized:false,maxVersion:'TLSv1.2'});
  await failed(certless);
  assert.equal(accepted,0,'Unauthorized connection reached worker');
  const input=new PassThrough(),output=new PassThrough();
  const parts=[];
  output.on('data',b=>parts.push(b));
  const result=runClient({psk,host,port,input,output});
  input.write('synthetic browser frame\n');
  assert.equal(await result,0);
  assert.equal(Buffer.concat(parts).toString(),'worker:synthetic browser frame\n');
  assert.equal(accepted,1);
  input.destroy();output.destroy();
  console.log('NOD_BROWSER_TLS_TRANSPORT_OK');
}finally{
  for(const peer of peers)peer.destroy();
  await Promise.all([new Promise(r=>gateway.close(r)),new Promise(r=>fixture.close(r))]);
  await rm(directory,{recursive:true,force:true});
}
