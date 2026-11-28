import assert from 'node:assert/strict';
import test from 'node:test';
import {resolveServerPeer as browser} from '../nod_browser_preflight/resolve-server-peer.mjs';
import {resolveServerPeer as workspace} from '../nod_workspace_preflight/resolve-server-peer.mjs';

const host = '65879d71-nod-native-preflight';
const answer = address => [{address,family:4}];
const dnsError = code => Object.assign(Error(code),{code});
for (const [component,resolvePeer] of [['Browser',browser],['Workspace',workspace]]) {
  test(component+' waits for late server DNS',async()=>{
    let calls=0, waits=0;
    const peer=await resolvePeer(host,{resolve:async(h,opts)=>{
      assert.equal(h,host);
      assert.deepEqual(opts,{all:true,family:4});
      if(++calls===1)throw dnsError('ENOTFOUND');
      if(calls===2)throw dnsError('EAI_AGAIN');
      return answer('172.30.33.7');
    },sleep:async()=>{waits++}});
    assert.equal(peer,'172.30.33.7');
    assert.equal(calls,3);
    assert.equal(waits,2);
  });
  test(component+' never accepts ambiguous or public DNS',async()=>{
    for(const result of [[],[...answer('172.30.33.7'),...answer('172.30.33.8')],answer('8.8.8.8'),answer('127.0.0.1'),answer('169.254.169.254')]){
      let calls=0;
      await assert.rejects(resolvePeer(host,{resolve:async()=>{calls++;return result},sleep:async()=>assert.fail('Must fail immediately')}));
      assert.equal(calls,1);
    }
    await assert.rejects(resolvePeer('example.com',{resolve:async()=>assert.fail('Unexpected DNS lookup')}));
  });
  test(component+' stops after bounded DNS failures',async()=>{
    let calls=0,waits=0;
    await assert.rejects(resolvePeer(host,{attempts:3,resolve:async()=>{calls++;throw dnsError('ENOTFOUND')},sleep:async()=>{waits++}}),{code:'ENOTFOUND'});
    assert.equal(calls,3);
    assert.equal(waits,2);
  });
  test(component+' retries stalled lookup with timeout',async()=>{
    let calls=0;
    const peer=await resolvePeer(host,{lookupTimeoutMs:5,attempts:2,resolve:()=>++calls===1?new Promise(()=>{}):Promise.resolve(answer('172.30.33.7')),sleep:async()=>{}});
    assert.equal(peer,'172.30.33.7');
    assert.equal(calls,2);
  });
}
