// Admission guard only: never claims a hard memory or storage quota.
import {readFileSync,statfsSync} from 'node:fs';
const MiB=1024*1024;
const hostReserve=512*MiB, containerReserve=256*MiB, diskReserve=512*MiB;
function readOptional(read,path){
  try{return read(path).trim();}
  catch(error){if(['ENOENT','ENOTDIR'].includes(error?.code))return undefined;throw error;}
}
function nonnegative(text){
  if(typeof text!=='string'||!/^\d+$/.test(text))throw Error('Invalid resource counter');
  return BigInt(text);
}
export function checkWorkspaceResources({
  read=path=>readFileSync(path,'utf8'),
  disk=()=>statfsSync('/data/workspaces',{bigint:true}),
}={}){
  try{
    const mem=read('/proc/meminfo').match(/^MemAvailable:\s*(\d+)\s+kB\s*$/m);
    if(!mem)throw Error('Missing host memory information');
    if(nonnegative(mem[1])*1024n<BigInt(hostReserve))return 'host-memory';
    const max=readOptional(read,'/sys/fs/cgroup/memory.max');
    if(max!==undefined&&max!=='max'){
      const limit=nonnegative(max);
      const current=nonnegative(read('/sys/fs/cgroup/memory.current').trim());
      if(limit-current<BigInt(containerReserve))return 'container-memory';
    }else if(max===undefined){
      const legacy=readOptional(read,'/sys/fs/cgroup/memory/memory.limit_in_bytes');
      if(legacy!==undefined){
        const limit=nonnegative(legacy);
        const current=nonnegative(read('/sys/fs/cgroup/memory/memory.usage_in_bytes').trim());
        if(limit-current<BigInt(containerReserve))return 'container-memory';
      }
    }
    const {bavail,bsize}=disk();
    if(typeof bavail!=='bigint'||typeof bsize!=='bigint'||bavail<0n||bsize<=0n)throw Error('Invalid disk information');
    if(bavail*bsize<BigInt(diskReserve))return 'disk-space';
    return null;
  }catch{return 'resource-information';}
}
// Upstream normal exit frames, not a transport failure: no command was spawned.
// A temporary refusal must not cause global command recovery.
export function resourceRefusalFrames(reason){
  const messages={
    'host-memory':'Not enough available host memory.',
    'container-memory':'Not enough available container memory.',
    'disk-space':'Not enough available workspace disk space.',
    'resource-information':'Unable to verify available workspace resources.',
  };
  if(!Object.hasOwn(messages,reason))throw Error('Invalid resource refusal');
  const data=Buffer.from(messages[reason]+' Retry when resources are available.\n').toString('base64');
  return JSON.stringify({type:'stderr',data})+'\n'+JSON.stringify({type:'exit',code:75,reason:null})+'\n';
}
