// HA adapter: reuse upstream lifecycle/IO and launch commands only in Workspace.
import {createCommandWorkspace} from './src/providers/docker/index.ts';
import {runWorkspaceCommand} from './src/providers/docker/command.ts';
import {createRemoteWorkspaceLauncher} from './workspace-launcher.mjs';
export function createHaWorkspace({workspaceRoot,container='nod-workspace-unavailable'}){
  const launcher=createRemoteWorkspaceLauncher();
  const workspace=createCommandWorkspace({
    workspaceRoot,
    instructions:'Isolated Home Assistant Workspace. Node, Python, LibreOffice, ffmpeg, OCR and document libraries are installed. Use /opt/nod-artifacts/bin/python for python-docx, openpyxl and pypdf. Network access is disabled here; use the browser for public websites. No connected CLIs, host Docker, Home Assistant files or server credentials are available. Keep outputs in this task workspace. Commands have a ten-minute hard deadline and a 16 MiB output limit. Task directories share the workspace user.',
    runCommand:(threadId,args,input)=>runWorkspaceCommand({
      ...input,container,threadId,args,spawn:launcher,
      // Pi sandbox defaults can exceed the worker's protocol limit.
      timeoutMs:Math.min(input.timeoutMs??30000,600000),
      maxBytes:Math.min(input.maxBytes??16*1024*1024,16*1024*1024),
    }),
  });
  console.log('NOD_HA_WORKSPACE_RUNTIME_CONNECTED');
  return workspace;
}
