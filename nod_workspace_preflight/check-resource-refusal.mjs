// Real worker and Unix socket in a disposable, low-memory CI container.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {readFileSync,existsSync} from 'node:fs';
import {createConnection} from 'node:net';
import {once} from 'node:events';
import {setTimeout as delay} from 'node:timers/promises';
const path='/run/nod-workspace/control.sock';
const marker='/data/workspaces/resource-test-marker';
const manifest=JSON.parse(readFileSync('/opt/nod-workspace-programs/manifest.json','utf8'));
const worker=spawn(process.execPath,['/app/probe-worker.mjs','--commands'],{stdio:['ignore','inherit','inherit']});
async function request(){
  const socket=createConnection(path);
  const chunks=[];
  const done=new Promise((resolve,reject)=>{
    socket.setTimeout(5000,()=>socket.destroy(Error('resource test deadline')));
    socket.on('error',reject);
    socket.on('data',chunk=>chunks.push(chunk));
    socket.on('end',()=>resolve(Buffer.concat(chunks).toString('utf8')));
  });
  socket.on('connect',()=>{
    socket.write(JSON.stringify({type:'command',threadId:'resource-test',program:manifest.command})+'\n'+
      JSON.stringify({args:['/usr/bin/python3','-I','-c',"from pathlib import Path; Path('/data/workspaces/resource-test-marker').touch()"],input:'',environment:{},timeoutMs:1000,maxBytes:4096})+'\n');
  });
  try{return (await done).trimEnd().split('\n').map(JSON.parse);}
  finally{socket.destroy();}
}
try{
  for(let i=0;i<50&&!existsSync(path);i++){
    if(worker.exitCode!==null)throw Error('worker exited');
    await delay(100);
  }
  assert.ok(existsSync(path));
  for(let i=0;i<2;i++){
    const frames=await request();
    assert.equal(frames.length,2);
    assert.equal(frames[0].type,'stderr');
    assert.match(Buffer.from(frames[0].data,'base64').toString(),/Not enough available container memory/);
    assert.deepEqual(frames[1],{type:'exit',code:75,reason:null});
    assert.equal(existsSync(marker),false);
  }
  assert.equal(worker.exitCode,null);
  console.log('NOD_WORKSPACE_REAL_RESOURCE_REFUSAL_OK');
}finally{
  if(worker.exitCode===null&&worker.signalCode===null){worker.kill('SIGTERM');await once(worker,'close');}
}
