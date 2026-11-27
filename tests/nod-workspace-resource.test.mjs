import assert from 'node:assert/strict';
import test from 'node:test';
import {checkWorkspaceResources,resourceRefusalFrames} from '../nod_workspace_preflight/resource-policy.mjs';
const MiB=1024n*1024n;
const absent=()=>{throw Object.assign(Error('missing'),{code:'ENOENT'});};
function fixture({host=1024,limit='max',current=0,free=1024,legacy=false,overrides={}}={}){
  const files={
    '/proc/meminfo':'MemAvailable: '+host*1024+' kB\n',
    ...(legacy?{
      '/sys/fs/cgroup/memory/memory.limit_in_bytes':limit,
      '/sys/fs/cgroup/memory/memory.usage_in_bytes':String(current),
    }:{
      '/sys/fs/cgroup/memory.max':limit,
      '/sys/fs/cgroup/memory.current':String(current),
    }),
    ...overrides,
  };
  return {read:path=>Object.hasOwn(files,path)?files[path]:absent(),
    disk:()=>({bavail:BigInt(free)*256n,bsize:4096n})};
}
test('allows a healthy host with no container memory limit',()=>{
  assert.equal(checkWorkspaceResources(fixture()),null);
});
test('refuses host memory below reserve',()=>{
  assert.equal(checkWorkspaceResources(fixture({host:511})),'host-memory');
  assert.equal(checkWorkspaceResources(fixture({host:512})),null);
});
test('checks cgroup v2 memory headroom',()=>{
  const limit=String(1024n*MiB);
  assert.equal(checkWorkspaceResources(fixture({limit,current:769n*MiB})),'container-memory');
  assert.equal(checkWorkspaceResources(fixture({limit,current:768n*MiB})),null);
});
test('checks cgroup v1 memory headroom',()=>{
  assert.equal(checkWorkspaceResources(fixture({legacy:true,limit:String(1024n*MiB),current:900n*MiB})),'container-memory');
});
test('refuses disk space below reserve',()=>{
  assert.equal(checkWorkspaceResources(fixture({free:511})),'disk-space');
  assert.equal(checkWorkspaceResources(fixture({free:512})),null);
});
test('refuses malformed or unavailable resource counters',()=>{
  assert.equal(checkWorkspaceResources(fixture({overrides:{'/proc/meminfo':'MemFree: 42 kB'}})),'resource-information');
  assert.equal(checkWorkspaceResources(fixture({limit:'oops'})),'resource-information');
  assert.equal(checkWorkspaceResources({...fixture(),disk:()=>{throw Error('statfs');}}),'resource-information');
});
test('refusal is an upstream-compatible normal command exit',()=>{
  for(const reason of ['host-memory','container-memory','disk-space','resource-information']){
    const frames=resourceRefusalFrames(reason).trimEnd().split('\n').map(JSON.parse);
    assert.equal(frames[0].type,'stderr');
    assert.match(Buffer.from(frames[0].data,'base64').toString(),/Retry when resources are available/);
    assert.deepEqual(frames[1],{type:'exit',code:75,reason:null});
  }
});
