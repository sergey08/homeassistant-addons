// One synthetic runtime task, real Workspace and Chromium; no model/account/MCP calls.
import assert from 'node:assert/strict';
import {mkdtemp,rm} from 'node:fs/promises';
import {join} from 'node:path';
import {randomUUID} from 'node:crypto';
import {createAgentRuntime} from './src/runtime/index.ts';
import {createSandbox} from './src/providers/pi/sandbox.ts';
import {createContainerBrowserComputer} from './src/providers/container-browser/index.ts';
import {createHaWorkspace} from './workspace-runtime.mjs';
const quote=value=>"'"+value.replaceAll("'","'\\''")+"'";
const ci=process.argv.includes('--ci');
const url=ci?'http://93.184.216.34/':'https://www.iana.org/help/example-domains';
const marker=ci?'Nod runtime browser fixture':'Example Domains';
const root=await mkdtemp('/tmp/nod-runtime-check-');
const workspace=createHaWorkspace({workspaceRoot:join(root,'workspaces')});
const computer=createContainerBrowserComputer({dataRoot:root,container:'nod-browser-unavailable',timeoutMs:20000});
assert.equal(workspace.connectedCliAvailable,false);
let taskMode=false,openingError;
let runtime;
const ids=[];
const agent={
  async open(options){
    const browser=options.tools.find(tool=>tool.name==='browser');
    assert.ok(browser, "Browser must be registered in chat and tasks");
    assert.equal(options.workspace.runConnectedCli,undefined);
    return{
      resumed:false,abort(){},dispose(){},
      async prompt(){
        try{
          if(taskMode){
            const sandbox=createSandbox(options.workspace,'Europe/Madrid');
            const bash=sandbox.find(tool=>tool.name==='bash');
            const write=sandbox.find(tool=>tool.name==='write');
            const read=sandbox.find(tool=>tool.name==='read');
            assert.ok(bash&&write&&read);
            const signal=new AbortController().signal;
            const invoke=async(tool,args)=>options.runTool(tool.name,args,()=>tool.execute('fixture-'+randomUUID(),args,signal,undefined,{cwd:options.workspace.path}));
            const result=await invoke(bash,{command:'printf runtime-fixture-ok'});
            assert.match(JSON.stringify(result),/runtime-fixture-ok/);
            const guard=await invoke(bash,{command:'/usr/bin/python3 -I -c '+quote('import os,pathlib,resource; s=pathlib.Path("/proc/self/status").read_text(); assert os.getuid()==1000; assert "SUPERVISOR_TOKEN" not in os.environ; assert not os.access("/run/nod-workspace-gateway/settings.json",os.R_OK); assert resource.getrlimit(resource.RLIMIT_NOFILE)==(128,128); assert resource.getrlimit(resource.RLIMIT_NPROC)==(256,256); assert "CapEff:\\t0000000000000000" in s; print("limits-verified")')});
            assert.match(JSON.stringify(guard),/limits-verified/);
            console.log('NOD_RUNTIME_WORKSPACE_EXEC_AND_GUARDS_OK');
            const path=options.workspace.path+'/drafts/fixture.txt';
            await invoke(write,{path,content:'synthetic runtime file'});
            assert.match(JSON.stringify(await invoke(read,{path})),/synthetic runtime file/);
            const payload=Buffer.alloc(600*1024,65);
            await workspace.writeArtifact(options.threadId,'chunked-fixture.bin',payload);
            assert.deepEqual(Buffer.from(await workspace.readArtifact(options.threadId,'chunked-fixture.bin',payload.length)),payload);
            await assert.rejects(workspace.readArtifact(options.threadId,'../escape',1024));
            console.log('NOD_RUNTIME_WORKSPACE_FILES_OK');
          }
          {
            const call=async args=>options.runTool('browser',args,()=>browser.execute(args));
            await call({action:'open',url});
            const page=await call({action:'snapshot'});
            assert.ok(JSON.stringify(page).includes(marker),'Expected public page text was not observed');
            const screenshot=await call({action:'screenshot'});
            assert.ok(screenshot.content.some(item=>item.type==='image'&&item.data.length>1000));
            console.log(taskMode ? 'NOD_RUNTIME_TASK_BROWSER_SNAPSHOT_AND_SCREENSHOT_OK' : 'NOD_RUNTIME_CHAT_BROWSER_SNAPSHOT_AND_SCREENSHOT_OK');
          }
          options.onEvent({type:'final',text:'Synthetic runtime fixture completed.'});
        }catch(error){openingError=error;throw error;}
      }
    };
  },
  dispose(){}
};
runtime=createAgentRuntime({agent,computer,workspace});
try{
  for(const work of [false,true]){
    taskMode=work;
    const id='runtime-'+randomUUID();ids.push(id);
    const context={threadId:id,sessionId:id,turnId:randomUUID(),prompt:'Synthetic adapter check.',history:[],
      workspacePath:join(root,'workspaces',id),signal:new AbortController().signal,attachments:[],timeZone:'Europe/Madrid',locale:'en-US',
      emit:async()=>{},reply:async()=>{},delta(){},
      publish:async()=>{throw Error('Publishing is outside this fixture');},
      requestCredential:async()=>{throw Error('Credentials are outside this fixture');},
      integration:async()=>{throw Error('Apps are outside this fixture');},
      manage:async()=>{throw Error('Management is outside this fixture');},
      ...(work?{taskContext:{id:randomUUID(),title:'Synthetic runtime check',brief:'Read public fixture with real browser.',doneWhen:'Snapshot and screenshot verified',revision:1}}:{})
    };
    const result=await runtime.runTurn(context);
    if(openingError)throw openingError;
    assert.equal(result.status,'succeeded');
  }
  console.log('NOD_RUNTIME_ADAPTER_TASK_OK');
}catch(error){
  console.error('NOD_RUNTIME_ADAPTER_TASK_FAILED '+String(error?.code??error?.name??'Error').replace(/[^A-Za-z0-9_]/g,''));
  process.exitCode=1;
}finally{
  for(const id of ids){
    const session=workspace.open({threadId:id,workspacePath:join(root,'workspaces',id),signal:new AbortController().signal});
    await session.exec('/usr/bin/python3 -I -c '+quote('import os,shutil; p=os.getcwd(); os.chdir("/var/tmp"); shutil.rmtree(p)'),{timeoutMs:10000}).catch(()=>{});
  }
  await runtime.dispose().catch(()=>{});
  await rm(root,{recursive:true,force:true});
}
