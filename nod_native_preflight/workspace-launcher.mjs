// Adapter for the upstream WorkspaceCommandLauncher, not attached to the agent yet.
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
const manifest=JSON.parse(readFileSync('/app/workspace-programs/manifest.json','utf8'));
export function createRemoteWorkspaceLauncher(){
  return (command,args,options)=>{
    if(command!=='docker'||options?.shell!==false||!Array.isArray(args)||args.length!==12||
      JSON.stringify(args.slice(0,5))!==JSON.stringify(['exec','-i','--user','node','--workdir'])||
      args[6]!=='nod-workspace-unavailable'||
      JSON.stringify(args.slice(7,11))!==JSON.stringify(['/usr/bin/python3','-I','-u','-c'])||
      createHash('sha256').update(args[11]).digest('hex')!==manifest.command)throw Error('Unsupported workspace launch');
    const cwd=args[5];
    const id=cwd==='/var/tmp'?'@recover':/^\/workspace\/([a-zA-Z0-9_-]{1,100})$/.exec(cwd)?.[1];
    if(!id)throw Error('Unsupported workspace directory');
    return spawn(process.execPath,['/app/workspace-command-client.mjs',id],{
      shell:false,env:{PATH:'/usr/local/bin:/usr/bin:/bin',LANG:'C.UTF-8'},stdio:['pipe','pipe','pipe']});
  };
}
