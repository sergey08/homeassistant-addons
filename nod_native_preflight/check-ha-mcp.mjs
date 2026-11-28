import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {once} from 'node:events';
import {createHaMcpBridge} from '/app/ha-mcp-bridge.mjs';
const secret='private_'+ 'x'.repeat(22);
let calls=0;
const fixture=createServer(async(req,res)=>{
  calls++;
  assert.equal(req.url,'/'+secret);
  assert.equal(req.headers.authorization,undefined);
  assert.equal(req.headers.cookie,undefined);
  const chunks=[];for await(const chunk of req)chunks.push(chunk);
  if(req.method==='DELETE'){res.writeHead(307,{location:'http://127.0.0.1:1/'+secret});res.end(secret);return;}
  if(req.method==='GET'){res.writeHead(200,{'content-type':'text/event-stream'});res.end('data: {"type":"refresh"}\n\n');return;}
  assert.equal(req.headers['mcp-protocol-version'],'2025-03-26');
  res.writeHead(200,{'content-type':'application/json','mcp-session-id':'synthetic-session','set-cookie':'ignore=1'});
  res.end(JSON.stringify({jsonrpc:'2.0',id:JSON.parse(Buffer.concat(chunks)).id,result:{tools:[]}}));
});
fixture.listen(0,'127.0.0.1');await once(fixture,'listening');
const bridge=createHaMcpBridge({upstreamHost:'127.0.0.1',upstreamPort:fixture.address().port});
bridge.listen(0,'127.0.0.1');await once(bridge,'listening');
const base='http://127.0.0.1:'+bridge.address().port;
try{
  const auth={authorization:'Bearer '+secret};
  assert.equal((await fetch(base+'/mcp')).status,401);
  assert.equal((await fetch(base+'/mcp',{headers:{authorization:'Bearer ../bad'}})).status,401);
  assert.equal((await fetch(base+'/other',{headers:auth})).status,403);
  assert.equal((await fetch(base+'/mcp',{headers:{...auth,origin:'https://evil.test'}})).status,403);
  assert.equal(calls,0);
  const response=await fetch(base+'/mcp',{method:'POST',headers:{...auth,'content-type':'application/json','mcp-protocol-version':'2025-03-26',cookie:'ignore=1'},body:JSON.stringify({jsonrpc:'2.0',id:1,method:'tools/list'})});
  assert.equal(response.status,200);
  assert.equal(response.headers.get('mcp-session-id'),'synthetic-session');
  assert.equal(response.headers.get('set-cookie'),null);
  assert.deepEqual(await response.json(),{jsonrpc:'2.0',id:1,result:{tools:[]}});
  assert.match(await(await fetch(base+'/mcp',{headers:auth})).text(),/data: /);
  const denied=await fetch(base+'/mcp',{method:'DELETE',headers:auth});
  assert.equal(denied.status,502);
  assert.ok(!(await denied.text()).includes(secret));
  assert.equal(calls,3);
  assert.equal((await fetch('http://127.0.0.1:9591/mcp')).status,401);
  console.log('NOD_NATIVE_HA_MCP_BRIDGE_OK');
}finally{await new Promise(r=>bridge.close(r));await new Promise(r=>fixture.close(r));}
