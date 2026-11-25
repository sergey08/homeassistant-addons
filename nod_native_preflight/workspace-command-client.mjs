// Private config file only; no PSK or arbitrary program on the command line.
import {readFileSync} from 'node:fs';
import {connectGateway} from './workspace-transport.mjs';
const id=process.argv[2];
if(id!=='@recover'&&!/^[a-zA-Z0-9_-]{1,100}$/.test(id??''))process.exit(1);
try{
  const config=JSON.parse(readFileSync('/run/nod-workspace-client/settings.json','utf8'));
  const manifest=JSON.parse(readFileSync('/app/workspace-programs/manifest.json','utf8'));
  const socket=connectGateway(config);
  let failed=false;
  socket.on('error',()=>{failed=true;});
  process.stdin.on('error',()=>socket.destroy());
  process.stdout.on('error',()=>socket.destroy());
  socket.once('secureConnect',()=>{
    socket.write(JSON.stringify(id==='@recover'?{type:'recover',program:manifest.command}:{type:'command',threadId:id,program:manifest.command})+'\n');
    process.stdin.pipe(socket);
    socket.pipe(process.stdout,{end:false});
  });
  socket.once('close',hadError=>{
    process.stdin.unpipe(socket);process.stdin.destroy();
    process.exitCode=(hadError||failed)?1:0;
  });
}catch{
  console.error('Workspace command transport unavailable');
  process.exitCode=1;
}
