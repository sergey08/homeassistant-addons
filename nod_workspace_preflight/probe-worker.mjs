// Transport preflight only. No caller-supplied commands, paths or code.
import net from 'node:net';
import {spawn} from 'node:child_process';
import {chmodSync} from 'node:fs';
import {openCommandSession} from './command-session.mjs';
const commandsEnabled=process.argv.includes('--commands');
const path='/run/nod-workspace/control.sock';
const server=net.createServer(socket=>{
  let buffer=Buffer.alloc(0),child,started=false,cancelled=false,closed=false,commandSession;
  const stop=()=>{if(child&&child.exitCode===null&&child.signalCode===null)child.kill('SIGKILL');};
  socket.setTimeout(15000,()=>socket.destroy());
  socket.on('error',()=>socket.destroy());
  socket.on('close',()=>{closed=true;stop();});
  socket.on('data',chunk=>{
    if(commandSession)return commandSession(chunk);
    buffer=Buffer.concat([buffer,chunk]);
    const first=buffer.indexOf(10);
    if((first<0&&buffer.length>4096)||first>4096)return socket.destroy();
    for(let i;(i=buffer.indexOf(10))>=0;){
      const line=buffer.subarray(0,i).toString('utf8');buffer=buffer.subarray(i+1);
      if(!started&&commandsEnabled&&line.startsWith('{')){
        try{commandSession=openCommandSession(socket,JSON.parse(line));commandSession(buffer);buffer=Buffer.alloc(0);}catch{socket.destroy();}
        return;
      }
      if(started){
        if(line!=='cancel'||cancelled||!child)return socket.destroy();
        cancelled=true;stop();continue;
      }
      if(line!=='probe'&&line!=='wait')return socket.destroy();
      started=true;
      const wait=line==='wait';
      const program=wait?'import time; time.sleep(60)':'print(42)';
      child=spawn('/opt/nod-artifacts/bin/python',['-I','-c',program],{
        cwd:'/workspace',env:{PATH:'/opt/nod-artifacts/bin:/usr/local/bin:/usr/bin:/bin',HOME:'/data/workspace-home',LANG:'C.UTF-8'},stdio:['ignore','pipe','ignore'],shell:false});
      child.on('error',()=>socket.destroy());
      child.stdout.on('data',chunk=>{if(!closed&&!wait&&chunk.toString().trim()==='42')socket.write('result:42\n');});
      child.once('close',(code,signal)=>{
        if(!closed)socket.end(cancelled&&signal==='SIGKILL'?'cancelled\n':code===0&&!wait?'exit:0\n':'error\n');
      });
      if(wait)socket.write('started\n');
    }
  });
});
server.maxConnections=4;
server.listen(path,()=>{chmodSync(path,0o660);console.log('NOD_WORKSPACE_PROBE_WORKER_READY');});
server.on('error',()=>process.exit(1));
