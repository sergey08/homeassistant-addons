// Synthetic credentials and fixed commands only. Run in the disposable CI peer.
import assert from 'node:assert/strict';
import {connectGateway} from '/app/transport.mjs';
const host='nod-workspace-ci-worker';
const psk='a'.repeat(64);
function request(key,command,{cancel=false}={}){
  return new Promise((resolve,reject)=>{
    const socket=connectGateway({psk:key,host,port:9593});
    let output='';
    const timer=setTimeout(()=>{socket.destroy();reject(Error('probe deadline'));},10000);
    socket.on('secureConnect',()=>socket.write(command+'\n'));
    socket.on('data',chunk=>{
      output+=chunk.toString();
      if(cancel&&output.includes('started\n')&&!output.includes('cancelled'))socket.write('cancel\n');
    });
    socket.on('error',error=>{clearTimeout(timer);reject(error);});
    socket.on('close',()=>{clearTimeout(timer);resolve(output);});
  });
}
assert.equal(await request(psk,'probe'),'result:42\nexit:0\n');
assert.equal(await request(psk,'wait',{cancel:true}),'started\ncancelled\n');
await assert.rejects(request('b'.repeat(64),'probe'));
assert.equal(await request(psk,'arbitrary command'),'');
assert.equal(await request(psk,'probe'),'result:42\nexit:0\n');
console.log('NOD_WORKSPACE_AUTHENTICATED_PROBE_OK');
console.log('NOD_WORKSPACE_CANCELLATION_OK');
console.log('NOD_WORKSPACE_WRONG_KEY_REJECTED');
