// Bounded fixed-command probe. No caller code, files, model calls or secrets in logs.
import {readFileSync} from 'node:fs';
import {setTimeout as delay} from 'node:timers/promises';
import {connectGateway} from './workspace-transport.mjs';
const config=JSON.parse(readFileSync('/run/nod-workspace-client/settings.json','utf8'));
function request(command,{cancel=false}={}){
  return new Promise((resolve,reject)=>{
    const socket=connectGateway(config);
    let output='',sentCancel=false,done=false;
    const finish=(error)=>{
      if(done)return;done=true;clearTimeout(timer);socket.destroy();
      if(error)reject(Error('workspace diagnostic request failed'));else resolve(output);
    };
    const timer=setTimeout(()=>finish(true),8000);
    socket.on('secureConnect',()=>socket.write(command+'\n'));
    socket.on('data',chunk=>{
      output+=chunk.toString('utf8');
      if(output.length>128)return finish(true);
      if(cancel&&!sentCancel&&output==='started\n'){sentCancel=true;socket.write('cancel\n');}
    });
    socket.on('error',()=>finish(true));
    socket.on('end',()=>finish(false));
    socket.on('close',hadError=>finish(hadError));
  });
}
let ready=false,phase='FIXED';
for(let attempt=0;attempt<5&&!ready;attempt++){
  try{
    if(await request('probe')!=='result:42\nexit:0\n')throw Error();
    ready=true;
  }catch{if(attempt<4)await delay(2000);}
}
try{
  if(!ready)throw Error();
  console.log('NOD_WORKSPACE_DIAGNOSTIC_EXEC_OK');
  if(await request('wait',{cancel:true})!=='started\ncancelled\n')throw Error();
  console.log('NOD_WORKSPACE_DIAGNOSTIC_CANCEL_OK');
  let rejected=false;
  try{rejected=(await request('arbitrary command')==='');}catch{rejected=true;}
  if(!rejected)throw Error();
  console.log('NOD_WORKSPACE_DIAGNOSTIC_ARBITRARY_REJECTED');
  if(await request('probe')!=='result:42\nexit:0\n')throw Error();
  console.log('NOD_WORKSPACE_DIAGNOSTIC_RECOVERY_OK');
  if(config.commandProbe===true){phase='UPSTREAM';await import('./workspace-command-diagnostic.mjs');}
}catch(error){
  console.error('NOD_WORKSPACE_DIAGNOSTIC_FAILED '+phase+' '+String(error?.code??error?.name??'Error').replace(/[^A-Za-z0-9_]/g,''));
  process.exitCode=1;
}
