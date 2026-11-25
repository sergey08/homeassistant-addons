// Carries upstream request/output/cancellation frames unchanged. No program upload.
import {spawn} from 'node:child_process';
import {readFileSync} from 'node:fs';
const manifest=JSON.parse(readFileSync('/opt/nod-workspace-programs/manifest.json','utf8'));
const stopProgram=readFileSync('/opt/nod-workspace-programs/stop.py','utf8');
const active=new Set();
let uncertain=false,recovering=false;
export function openCommandSession(socket,header){
  const recover=header?.type==='recover';
  if(!header||header.program!==manifest.command||Object.keys(header).sort().join(',')!==(recover?'program,type':'program,threadId,type')||
    (!recover&&(header.type!=='command'||typeof header.threadId!=='string'||!/^[a-zA-Z0-9_-]{1,100}$/.test(header.threadId))))throw Error();
  let pending=Buffer.alloc(0),child,started=false,closed=false,confirmed=false,stdoutPending='',timer,finished=false;
  const initial=setTimeout(()=>socket.destroy(),5000);
  socket.setTimeout(0);
  function stop(){
    if(finished)return;
    child?.stdin.end();
    clearTimeout(timer);
    timer=setTimeout(()=>{
      uncertain=true;
      child?.kill('SIGKILL');
      socket.destroy();
    },7500);
    timer.unref();
  }
  socket.once('close',()=>{closed=true;clearTimeout(initial);if(child)stop();});
  function append(chunk){
    if(closed)return;
    pending=Buffer.concat([pending,chunk]);
    const limit=started?1024:1024*1024;
    const first=pending.indexOf(10);
    if((first<0&&pending.length>limit)||first>limit){socket.destroy();return;}
    let index;
    while((index=pending.indexOf(10))>=0){
      const line=pending.subarray(0,index);
      pending=pending.subarray(index+1);
      if(started){
        if(line.toString('utf8')!=='{"type":"cancel"}'){socket.destroy();return;}
        child.stdin.write(Buffer.concat([line,Buffer.from('\n')]));
        continue;
      }
      let request;
      try{
        request=JSON.parse(line);
        if(!request||typeof request!=='object'||Array.isArray(request)||
          Object.keys(request).some(k=>!['args','input','environment','timeoutMs','maxBytes'].includes(k))||
          !Array.isArray(request.args)||request.args.length<1||request.args.length>128||
          !request.args.every(v=>typeof v==='string'&&!v.includes('\0'))||
          typeof request.input!=='string'||!request.environment||Array.isArray(request.environment)||
          Object.keys(request.environment).length||
          !Number.isInteger(request.timeoutMs)||request.timeoutMs<1||request.timeoutMs>600000||
          !Number.isInteger(request.maxBytes)||request.maxBytes<1||request.maxBytes>16*1024*1024)throw Error();
        if(recover){
          if(recovering)throw Error();
          if(JSON.stringify(request.args)!==JSON.stringify(['/usr/bin/python3','-I','-c',stopProgram,'/proc'])||
            request.timeoutMs>30000||request.maxBytes>4096||request.input)throw Error();
        }else if(uncertain||recovering||active.size>=2)throw Error();
      }catch{socket.destroy();return;}
      started=true;clearTimeout(initial);
      child=spawn('/usr/bin/python3',['-I','-u','/app/command-entry.py',recover?'@recover':header.threadId],{
        cwd:'/var/tmp',shell:false,env:{PATH:'/opt/nod-artifacts/bin:/usr/local/bin:/usr/bin:/bin',HOME:'/data/workspace-home',LANG:'C.UTF-8'},
        stdio:['pipe','pipe','pipe']});
      const earlier=recover?[...active].map(process=>new Promise(resolve=>{
        if(process.exitCode!==null||process.signalCode!==null)resolve();else process.once('close',resolve);
      })):[];
      if(recover)recovering=true;
      active.add(child);
      child.on('error',()=>socket.destroy());
      child.stdin.on('error',()=>socket.destroy());
      // A hard wall deadline also covers blocked/spoofed streams and lost peers.
      timer=setTimeout(stop,request.timeoutMs+1000);
      timer.unref();
      child.stdout.on('data',bytes=>{
        stdoutPending+=bytes.toString('utf8');
        let end;
        while((end=stdoutPending.indexOf('\n'))>=0){
          const frame=stdoutPending.slice(0,end);stdoutPending=stdoutPending.slice(end+1);
          try{const value=JSON.parse(frame);if(value.type==='exit'&&Number.isInteger(value.code))confirmed=true;}catch{}
        }
        if(stdoutPending.length>32768){uncertain=true;socket.destroy();return;}
        if(!closed&&!socket.write(bytes))child.stdout.pause();
      });
      socket.on('drain',()=>child.stdout.resume());
      // Transport stderr is deliberately generic; user stderr is in upstream frames.
      child.stderr.resume();
      child.once('close',async code=>{
        finished=true;active.delete(child);clearTimeout(timer);
        if(!confirmed||code!==0)uncertain=true;
        else if(recover){await Promise.allSettled(earlier);if(active.size===0)uncertain=false;}
        if(recover)recovering=false;
        if(!closed){if(confirmed&&code===0)socket.end();else socket.destroy();}
      });
      child.stdin.write(Buffer.concat([line,Buffer.from('\n')]));
    }
    if(pending.length>(started?1024:1024*1024))socket.destroy();
  }
  return append;
}
