// Isolated test server, no external model service or real credentials.
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
const model='ci-local-tools:4b', nonTool='ci-no-tools:4b';
const endpoint='http://nod-model-fixture:11434';
const base='http://nod-ingress:8099';
const admin={'x-remote-user-id':'ci-admin','x-remote-user-groups':'system-admin'};
const marked={...admin,'x-nod-ingress-request':'1','content-type':'application/json'};
const models='/api/models';
const mode=process.argv[2];
if(mode==='serve'){
  createServer(async(req,res)=>{
    const path=req.url.replace(/^\/second(?=\/)/,'');
    const json=(data,status=200)=>{res.writeHead(status,{'Content-Type':'application/json'});res.end(JSON.stringify(data));};
    if(req.method==='GET'&&path==='/v1/models')return json({object:'list',data:[{id:model},{id:nonTool}]});
    if(req.method==='GET'&&path==='/api/version')return json({version:'0.0.0-ci'});
    if(req.method==='GET'&&path==='/api/ps')return json({models:[{name:model,context_length:65536}]});
    if(req.method==='POST'&&path==='/api/show'){
      let input='';for await(const chunk of req)input+=chunk;
      const name=JSON.parse(input).model;
      return json({capabilities:name===model?['completion','tools']:['completion'],model_info:{'qwen3.context_length':131072},parameters:'num_ctx 65536'});
    }
    // A selection check may make a synthetic completion request.
    if(req.method==='POST'&&path==='/v1/chat/completions'){
      let input='';for await(const chunk of req)input+=chunk;
      const request=JSON.parse(input);
      const common={id:'chatcmpl-ci',created:1,model};
      const usage={prompt_tokens:2,completion_tokens:1,total_tokens:3};
      if(request.stream){
        res.writeHead(200,{'Content-Type':'text/event-stream'});
        for(const chunk of [{...common,object:'chat.completion.chunk',choices:[{index:0,delta:{role:'assistant',content:'OK'},finish_reason:null}]},{...common,object:'chat.completion.chunk',choices:[{index:0,delta:{},finish_reason:'stop'}],usage}]){
          res.write('data: '+JSON.stringify(chunk)+'\n\n');
        }
        res.end('data: [DONE]\n\n');return;
      }
      return json({...common,object:'chat.completion',choices:[{index:0,message:{role:'assistant',content:'OK'},finish_reason:'stop'}],usage});
    }
    json({error:'Unsupported fixture route'},404);
  }).listen(11434,'0.0.0.0',()=>console.log('NOD_LOCAL_MODEL_FIXTURE_READY'));
}else{
  const request=(path,method='GET',body,headers=method==='GET'?admin:marked)=>
    fetch(base+path,{method,headers,...(body===undefined?{}:{body:JSON.stringify(body)}),signal:AbortSignal.timeout(60000)});
  async function ok(path,method='GET',body){
    const res=await request(path,method,body);
    assert.equal(res.status,200,path+' '+method+' '+await res.clone().text());
    return res.json();
  }
  const choice=row=>({connectionId:row.id,modelId:model,effort:row.models[0].efforts[0]});
  const get=async()=>ok(models);
  if(mode==='connect'){
    for(const path of [models+'/endpoints','/api/memory','/api/speech']){
      const method=path.endsWith('endpoints')?'POST':'GET';
      const body=method==='POST'?{url:endpoint+'/v1',key:''}:undefined;
      assert.equal((await request(path,method,body,{})).status,403);
      assert.equal((await request(path,method,body,{...marked,'x-remote-user-groups':'system-users'})).status,403);
      assert.equal((await request(path,method,body,{...marked,'x-nod-account':'wrong-account'})).status,401);
    }
    assert.equal((await request(models+'/endpoints','POST',{url:endpoint+'/v1',key:''},{...admin,'content-type':'application/json'})).status,403);
    assert.equal((await request(models+'/endpoints','POST',{}, {...marked,'content-type':'text/plain'})).status,403);
    assert.equal((await request(models+'/endpoints','POST',{})).status,400);
    assert.equal((await request(models+'/endpoints','GET')).status,404);
    assert.equal((await request(models+'/connections/not-a-uuid','DELETE')).status,405);
    assert.equal((await request(models+'/connections/%2f/refresh','POST')).status,405);
    assert.equal((await request(models+'/oauth/callback')).status,404);
    assert.equal((await request(models+'/unknown','POST',{})).status,405);
    const before=await get();
    let data=await ok(models+'/endpoints','POST',{url:endpoint+'/v1',key:''});
    const first=data.connections.find(row=>row.provider==='compatible'&&row.models.some(m=>m.id===model));
    assert.ok(first);assert.equal(first.status,'connected');
    assert.deepEqual(first.models.map(m=>m.id),[model]);
    assert.equal(first.models[0].contextWindow,65536);
    assert.ok(first.models[0].efforts.length);
    for(const row of before.connections)assert.ok(data.connections.some(x=>x.id===row.id));
    if(before.connections.some(row=>row.id===before.selection?.connectionId&&row.status==='connected'))assert.deepEqual(data.selection,before.selection);
    data=await ok(models+'/endpoints','POST',{url:endpoint+'/v1',key:''});
    assert.equal(data.connections.filter(row=>row.id===first.id).length,1);
    assert.equal(data.connections.length,before.connections.length+1);
    data=await ok(models+'/connections/'+first.id+'/refresh','POST');
    assert.equal(data.connections.find(row=>row.id===first.id).models[0].contextWindow,65536);
    const selection=choice(first);
    data=await ok(models+'/selection','PUT',selection);assert.deepEqual(data.selection,selection);
    for(const lane of ['schedule','background']){
      data=await ok(models+'/routes','PUT',{lane,route:selection});assert.deepEqual(data.routes[lane],selection);
    }
    data=await ok(models+'/endpoints','POST',{url:endpoint+'/second/v1',key:''});
    assert.deepEqual(data.selection,selection);
    const second=data.connections.find(row=>row.id!==first.id&&row.provider==='compatible'&&row.models.some(m=>m.id===model)&&!before.connections.some(x=>x.id===row.id));
    assert.ok(second);const backup=choice(second);
    data=await ok(models+'/backups','PUT',{backups:[backup]});assert.deepEqual(data.backups,[backup]);
    const memory=await ok('/api/memory');assert.equal(typeof memory.saving,'boolean');
    const memoryExport=await request('/api/memory/export');
    assert.equal(memoryExport.status,200);assert.match(memoryExport.headers.get('content-type'),/^text\/markdown/);
    assert.match(memoryExport.headers.get('content-disposition'),/^attachment;/);
    assert.equal(memoryExport.headers.get('x-content-type-options'),'nosniff');
    const voice=await ok('/api/speech');assert.equal(typeof voice.transcription,'boolean');assert.ok(Array.isArray(voice.voices));
    await ok('/api/speech/voices/refresh','POST',{});
    assert.equal((await request('/api/speech/preview','POST',{voice:'invalid-ci-voice'})).status,400);
    console.log('NOD_LOCAL_MODEL_CONNECTION_AND_SETTINGS_OK');
  }else if(mode==='restart'){
    let data=await get();
    const first=data.connections.find(row=>row.id===data.selection?.connectionId);
    assert.ok(first&&first.provider==='compatible'&&first.models[0].id===model);
    assert.deepEqual(data.routes.schedule,data.selection);
    assert.deepEqual(data.routes.background,data.selection);
    assert.equal(data.backups.length,1);
    const backup=data.backups[0].connectionId;
    data=await ok(models+'/connections/'+backup,'DELETE');
    assert.ok(!data.connections.some(row=>row.id===backup));assert.equal(data.backups.length,0);
    assert.equal((await request(models+'/connections/'+first.id)).status,404);
    data=await ok(models+'/connections/'+first.id,'DELETE');
    assert.ok(!data.connections.some(row=>row.id===first.id));assert.equal(data.selection,null);
    assert.ok(!data.routes.schedule&&!data.routes.background);
    console.log('NOD_LOCAL_MODEL_PERSISTENCE_AND_DELETE_OK');
  }else throw Error('Unknown fixture mode');
}
