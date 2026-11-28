// Preserve upstream task/background gating; replace only the Workspace adapter.
import {readFileSync,writeFileSync} from 'node:fs';
const file='/app/src/server/composition.ts';
let source=readFileSync(file,'utf8');
const imported="import { createDockerWorkspace } from '../providers/docker/index.ts';";
const block=`    workspace: createDockerWorkspace({
      container: env.WORKSPACE_CONTAINER || 'nod-workspace',
      workspaceRoot: join(dataRoot, 'workspaces'),
    }),`;
if(source.split(imported).length!==2||source.split(block).length!==2)throw Error('Workspace composition anchor changed');
source=source.replace(imported,imported+"\nimport { createHaWorkspace } from '/app/workspace-runtime.mjs';");
source=source.replace(block,`    workspace: env.NOD_HA_WORKSPACE_REMOTE === '1'
      ? createHaWorkspace({
          container: env.WORKSPACE_CONTAINER || 'nod-workspace-unavailable',
          workspaceRoot: join(dataRoot, 'workspaces'),
        })
      : createDockerWorkspace({
          container: env.WORKSPACE_CONTAINER || 'nod-workspace',
          workspaceRoot: join(dataRoot, 'workspaces'),
        }),`);
writeFileSync(file,source);
console.log('NOD_HA_WORKSPACE_COMPOSITION_PATCH_OK');
