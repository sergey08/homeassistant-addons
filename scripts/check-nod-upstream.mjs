import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const read = p => readFileSync(resolve(root, p), 'utf8');
const manifest = JSON.parse(read('nod-upstream.json'));
if (manifest.repository !== 'n8n-io/nod' ||
    !/^nod-v\d+\.\d+\.\d+$/.test(manifest.tag) ||
    !/^[0-9a-f]{40}$/.test(manifest.revision)) {
  throw new Error('Invalid Nod upstream manifest');
}
const args = process.argv.slice(2);
if (args.length > 1 || (args.length && args[0] !== '--write')) {
  throw new Error('Usage: node scripts/check-nod-upstream.mjs [--write]');
}
const appRoles = {
  Server: 'nod_native_preflight',
  Browser: 'nod_browser_preflight',
  Workspace: 'nod_workspace_preflight',
};
const stageOrder = [ 'dev', 'alpha', 'beta', 'rc', undefined ];
const number = '0|[1-9][0-9]{0,7}';
const appVersion = new RegExp(
  '^(' + number + ')\\.(' + number + ')\\.(' + number + ')' +
  '(?:-(dev|alpha|beta|rc)\\.(' + number + '))?
  ['nod_native_preflight/Dockerfile', /^(?:RUN git init).*git fetch --depth=1 origin [0-9a-f]{40}.*$/gm, 1, 2],
  ['nod_browser_preflight/Dockerfile', /^ARG NOD_UPSTREAM_REV=[0-9a-f]{40}$/gm, 1, 1],
  ['nod_workspace_preflight/Dockerfile', /^(?:RUN git init).*git fetch --depth=1 origin [0-9a-f]{40}.*$/gm, 1, 2],
  ['.github/workflows/nod-browser-worker.yml', /^.*git -C .* (?:fetch --depth=1 origin|rev-parse HEAD\)" =) [0-9a-f]{40}$/gm, 2, 1],
];
const changes = [];
for (const [path, pattern, expected, pins] of targets) {
  const before = read(path);
  const matches = [...before.matchAll(pattern)];
  if (matches.length !== expected || matches.some(m => (m[0].match(/\b[0-9a-f]{40}\b/g) || []).length !== pins)) {
    throw new Error('Upstream pin anchors changed: ' + path);
  }
  const after = before.replace(pattern, line => line.replace(/\b[0-9a-f]{40}\b/g, manifest.revision));
  if (before !== after) changes.push([path, after]);
}
if (changes.length && !args.length) {
  throw new Error('Nod upstream pin mismatch: ' + changes.map(([p]) => p).join(', ') +
    '. Run node scripts/check-nod-upstream.mjs --write and review the diff.');
}
for (const [path, content] of changes) writeFileSync(resolve(root, path), content);
console.log('NOD_UPSTREAM_OK ' + manifest.tag + ' ' + manifest.revision);

);
function versionSet(versions) {
  if (!versions || Object.keys(versions).length !== Object.keys(appRoles).length) {
    throw new Error('Invalid Nod app version set');
  }
  return Object.entries(appRoles).map(([role, path]) => {
    const value = versions[role];
    const match = typeof value === 'string' && appVersion.exec(value);
    if (!match || match[0] !== value) {
      throw new Error('Invalid Nod app version for ' + path);
    }
    const [, major, minor, patch, stage, build] = match;
    return [Number(major), Number(minor), Number(patch), stageOrder.indexOf(stage), Number(build || 0)];
  });
}
const upgrade = manifest.ha_upgrade;
if (!upgrade || Object.keys(upgrade).length !== 3 || upgrade.schema !== 1 ||
    !Array.isArray(upgrade.supported_from) || !upgrade.supported_from.length) {
  throw new Error('Invalid Nod coordinated upgrade schema');
}
const target = versionSet(upgrade.target);
const seen = new Set();
for (const baseline of upgrade.supported_from) {
  const source = versionSet(baseline);
  const ordered = source.map((version, i) =>
    version.map((part, j) => part - target[i][j]).find(part => part !== 0) || 0
  );
  const key = JSON.stringify(source);
  if (seen.has(key) || ordered.every(part => part === 0) || ordered.some(part => part > 0)) {
    throw new Error('Invalid Nod coordinated upgrade transition');
  }
  seen.add(key);
}
for (const [role, path] of Object.entries(appRoles)) {
  const matches = [...read(path + '/config.yaml').matchAll(/^version: "([^"]+)"[ \t]*$/gm)];
  if (matches.length !== 1 || matches[0][1] !== upgrade.target[role]) {
    throw new Error('Nod upgrade target does not match ' + path + '/config.yaml');
  }
}
const targets = [
  ['nod_native_preflight/Dockerfile', /^(?:RUN git init).*git fetch --depth=1 origin [0-9a-f]{40}.*$/gm, 1, 2],
  ['nod_browser_preflight/Dockerfile', /^ARG NOD_UPSTREAM_REV=[0-9a-f]{40}$/gm, 1, 1],
  ['nod_workspace_preflight/Dockerfile', /^(?:RUN git init).*git fetch --depth=1 origin [0-9a-f]{40}.*$/gm, 1, 2],
  ['.github/workflows/nod-browser-worker.yml', /^.*git -C .* (?:fetch --depth=1 origin|rev-parse HEAD\)" =) [0-9a-f]{40}$/gm, 2, 1],
];
const changes = [];
for (const [path, pattern, expected, pins] of targets) {
  const before = read(path);
  const matches = [...before.matchAll(pattern)];
  if (matches.length !== expected || matches.some(m => (m[0].match(/\b[0-9a-f]{40}\b/g) || []).length !== pins)) {
    throw new Error('Upstream pin anchors changed: ' + path);
  }
  const after = before.replace(pattern, line => line.replace(/\b[0-9a-f]{40}\b/g, manifest.revision));
  if (before !== after) changes.push([path, after]);
}
if (changes.length && !args.length) {
  throw new Error('Nod upstream pin mismatch: ' + changes.map(([p]) => p).join(', ') +
    '. Run node scripts/check-nod-upstream.mjs --write and review the diff.');
}
for (const [path, content] of changes) writeFileSync(resolve(root, path), content);
console.log('NOD_UPSTREAM_OK ' + manifest.tag + ' ' + manifest.revision);
