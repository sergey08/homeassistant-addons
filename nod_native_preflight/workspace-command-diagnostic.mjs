// Synthetic upstream-protocol checks. Not connected to runtime task tools.
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
import {runWorkspaceCommand,WorkspaceCommandError} from './src/providers/docker/command.ts';
import {createRemoteWorkspaceLauncher} from './workspace-launcher.mjs';
const launcher=createRemoteWorkspaceLauncher();
const id='protocol-'+randomUUID();
const options={container:'nod-workspace-unavailable',threadId:id,spawn:launcher,timeoutMs:10000};
const run=(args,extra={})=>runWorkspaceCommand({...options,args,...extra});
const python=(program,extra={})=>run(['/usr/bin/python3','-I','-c',program],extra);
const checkStopped=async pid=>{
  const result=await python('import pathlib; p=pathlib.Path("/proc/'+pid+'/stat"); print("gone" if not p.exists() else p.read_text().rsplit(")",1)[1].split()[0])');
  assert.match(result.stdout.toString().trim(),/^(gone|Z|X)$/);
};
try{
  const result=await python('import sys; print(42); print("fixture-error",file=sys.stderr); sys.exit(7)');
  assert.equal(result.stdout.toString(),'42\n');assert.equal(result.stderr.toString(),'fixture-error\n');assert.equal(result.exitCode,7);
  const unicode='á'.repeat(40000);
  assert.equal((await python('import sys; print(len(sys.stdin.read()))',{input:unicode})).stdout.toString(),'40000\n');
  console.log('NOD_WORKSPACE_PROTOCOL_FRAMES_OK');
  let streamed='';
  await python('import sys,time; print("stream",flush=True); time.sleep(.1); print("done",flush=True)',{onData:bytes=>{streamed+=bytes.toString();}});
  assert.equal(streamed,'stream\ndone\n');
  console.log('NOD_WORKSPACE_PROTOCOL_STREAMING_OK');
  const abort=new AbortController();let childPid,pidLine='';
  await assert.rejects(python('import subprocess,sys,time; p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(60)"]); print(p.pid,flush=True); time.sleep(60)',{
    signal:abort.signal,onData:bytes=>{pidLine+=bytes.toString();if(pidLine.includes('\n')){childPid=Number(pidLine.trim());abort.abort();}}
  }),error=>error instanceof WorkspaceCommandError&&!error.uncertain&&/cancelled/i.test(error.message));
  assert.ok(Number.isInteger(childPid)&&childPid>1);await checkStopped(childPid);
  console.log('NOD_WORKSPACE_PROTOCOL_CANCEL_CONFIRMED');
  await assert.rejects(python('import time; time.sleep(5)',{timeoutMs:200}),error=>error instanceof WorkspaceCommandError&&!error.uncertain&&/limit/.test(error.message));
  await assert.rejects(python('print("x"*100000)',{maxBytes:1024}),error=>error instanceof WorkspaceCommandError&&!error.uncertain&&/limit/.test(error.message));
  console.log('NOD_WORKSPACE_PROTOCOL_LIMITS_OK');
  const artifacts=await run(['/opt/nod-artifacts/bin/python','-I','-c','import docx,openpyxl; from pypdf import PdfWriter,PdfReader; d=docx.Document(); d.add_paragraph("synthetic"); d.save("fixture.docx"); b=openpyxl.Workbook(); b.active["A1"]=42; b.save("fixture.xlsx"); w=PdfWriter(); w.add_blank_page(width=200,height=200); w.write("fixture.pdf"); assert docx.Document("fixture.docx").paragraphs[0].text=="synthetic"; assert openpyxl.load_workbook("fixture.xlsx").active["A1"].value==42; assert len(PdfReader("fixture.pdf").pages)==1; print("artifacts-ok")']);
  assert.equal(artifacts.stdout.toString(),'artifacts-ok\n');
  console.log('NOD_WORKSPACE_PROTOCOL_FILES_OK');
  let client;let interruptedPid,interruptedLine='';
  const broken=runWorkspaceCommand({...options,args:['/usr/bin/python3','-I','-c','import os,time; print(os.getpid(),flush=True); time.sleep(60)'],
    spawn:(...args)=>{client=launcher(...args);return client;},onData:bytes=>{interruptedLine+=bytes.toString();if(interruptedLine.includes('\n')){interruptedPid=Number(interruptedLine.trim());client.kill('SIGKILL');}}});
  let failure;try{await broken;}catch(error){failure=error;}
  assert.ok(failure instanceof WorkspaceCommandError&&failure.uncertain&&failure.stop);
  await failure.stop();await checkStopped(interruptedPid);
  console.log('NOD_WORKSPACE_PROTOCOL_DISCONNECT_RECOVERED');
  const symlinkId='symlink-'+randomUUID();
  await python('import os; os.symlink("/var/tmp","/data/workspaces/'+symlinkId+'")');
  try{
    let rejected;try{await runWorkspaceCommand({...options,threadId:symlinkId,args:['/usr/bin/python3','-c','print("must-not-run")']});}catch(error){rejected=error;}
    assert.ok(rejected instanceof WorkspaceCommandError&&rejected.uncertain&&rejected.stop);
    await rejected.stop();
  }finally{await python('import os; os.unlink("/data/workspaces/'+symlinkId+'")');}
  console.log('NOD_WORKSPACE_PROTOCOL_SYMLINK_REJECTED');
  assert.equal((await python('print(42)')).stdout.toString(),'42\n');
  console.log('NOD_WORKSPACE_PROTOCOL_RECOVERY_OK');
}finally{
  await python('import os,shutil; p=os.getcwd(); os.chdir("/var/tmp"); shutil.rmtree(p)').catch(()=>{});
}
