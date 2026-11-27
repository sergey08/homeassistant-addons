import assert from 'node:assert/strict';
import {createHash, randomUUID} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {createServer} from 'node:http';
import pg from 'pg';
import {openVaultValue} from './src/server/vault-crypto.ts';
import {createDiscoveredTransport, ownerFetch} from './src/providers/discovered/remote.ts';

const [, , mode, snapshot] = process.argv;
assert.ok(mode === 'seed' || mode === 'verify');
const origin = 'http://localhost:4310';
const fixtureOrigin = 'http://127.0.0.1:11434';
const site = 'https://nod-migration.invalid';
const modelName = 'ci-local-tools:4b';
const modelKey = 'synthetic-migration-model-token';
const mcpKey = 'synthetic-migration-mcp-token';
const vaultPassword = 'synthetic-migration-vault-password';
const vaultLabel = 'Nod CI migration login';
const connectorName = 'Nod CI MCP';
const connectorAccount = 'Nod CI synthetic account';
const memory = 'Nod CI migration memory: prefer blue folders.';
const artifact = '# Nod migration artifact\nPersisted UTF-8 bytes: café\n';
const scheduleTitle = 'Nod CI migration schedule';
const schedulePrompt = 'Synthetic check. Do not use any tools.';
const messages = ['Nod CI synthetic question', 'Nod CI synthetic answer'];
const secrets = readFileSync('/data/nod-native-v1/secrets');
const [databasePassword, token, vaultKey] = secrets.toString('utf8').split('\n');
assert.match(token, /^[a-f0-9]{64}$/);
const db = new pg.Pool({
  host: '127.0.0.1', user: 'nod', database: 'nod', password: databasePassword,
});

async function request(path, method = 'GET', body) {
  const headers = {authorization: 'Bearer ' + token, origin};
  if (body !== undefined && !(body instanceof FormData)) {
    headers['content-type'] = 'application/json';
    body = JSON.stringify(body);
  }
  const response = await fetch(origin + path, {
    method, headers, body, redirect: 'error', signal: AbortSignal.timeout(30000),
  });
  assert.ok(response.ok, method + ' ' + path + ' returned HTTP ' + response.status);
  return response;
}

async function json(path, method, body) {
  return (await request(path, method, body)).json();
}

function fingerprint(bytes) {
  return createHash('sha256').update(bytes).digest('hex');
}

let authenticatedModelReads = 0;
const fixture = createServer(async (req, res) => {
  try {
    const reply = (value, status = 200) => {
      res.writeHead(status, {'Content-Type': 'application/json'});
      res.end(JSON.stringify(value));
    };
    if (req.url === '/api/version') return reply({version: '0.0.0-ci'});
    if (req.url === '/api/ps') return reply({models: [{name: modelName, context_length: 65536}]});
    if (req.url === '/api/show') {
      return reply({capabilities: ['completion', 'tools'], model_info: {'qwen3.context_length': 65536}});
    }
    if (req.url === '/v1/models') {
      if (req.headers.authorization !== 'Bearer ' + modelKey) return reply({}, 401);
      authenticatedModelReads += 1;
      return reply({object: 'list', data: [{id: modelName}]});
    }
    if (req.url !== '/mcp') return reply({}, 404);
    if (req.headers.authorization !== 'Bearer ' + mcpKey) return reply({}, 401);
    if (req.method !== 'POST') return res.writeHead(405).end();
    let bytes = '';
    for await (const chunk of req) bytes += chunk;
    const {id, method, params} = JSON.parse(bytes);
    if (id === undefined) return res.writeHead(202).end();
    if (method === 'initialize') {
      return reply({jsonrpc: '2.0', id, result: {
        protocolVersion: params.protocolVersion, capabilities: {tools: {}},
        serverInfo: {name: 'Nod migration fixture', version: '1.0.0'},
      }});
    }
    if (method === 'tools/list') {
      return reply({jsonrpc: '2.0', id, result: {
        tools: [{name: 'ci_read_marker', description: 'Read a synthetic marker', inputSchema: {type: 'object'}}],
      }});
    }
    return reply({jsonrpc: '2.0', id, error: {code: -32601, message: 'Method not found'}});
  } catch {
    res.writeHead(500).end();
  }
});
await new Promise((resolve, reject) => {
  fixture.once('error', reject);
  fixture.listen(11434, '127.0.0.1', resolve);
});

async function seed() {
  await json('/api/account', 'PATCH', {theme: 'dark', usageData: false});
  await json('/api/memory/notes', 'POST', {area: 'preferences', text: memory});
  const saved = await json('/api/vault', 'POST', {
    label: vaultLabel, origin: site, username: 'synthetic-user', password: vaultPassword,
  });
  const runAt = new Date(Date.now() + 7 * 86400000).toISOString();
  const schedule = await json('/api/schedules', 'POST', {
    kind: 'once', title: scheduleTitle, prompt: schedulePrompt, timeZone: 'Etc/UTC', runAt,
  });
  await json('/api/schedules/' + schedule.id, 'PATCH', {enabled: false});
  const modelData = await json('/api/models/endpoints', 'POST', {url: fixtureOrigin + '/v1', key: modelKey});
  const model = modelData.connections.find(row =>
    row.provider === 'compatible' && row.models.some(choice => choice.id === modelName),
  );
  assert.ok(model);
  const proposal = await json('/api/apps/mcp', 'POST', {
    name: connectorName, auth: 'bearer', endpoint: fixtureOrigin + '/mcp',
  });
  const proposalId = new URL(proposal.url, origin).searchParams.get('connect');
  assert.match(proposalId, /^[a-f0-9-]{36}$/);
  const connected = await json('/api/apps/discovery/' + proposalId + '/complete', 'POST', {
    token: mcpKey, accountName: connectorAccount,
  });
  assert.equal(connected.ok, true);
  const connector = (await json('/api/apps')).find(row => row.accountName === connectorAccount);
  assert.ok(connector);

  const form = new FormData();
  form.append('file', new Blob([artifact], {type: 'text/markdown'}), 'migration.md');
  const upload = await json('/api/uploads', 'POST', form);
  // Use the existing active thread and insert finished messages without calling an AI provider.
  await json('/api/messages');
  const ids = messages.map(() => randomUUID());
  const active = await db.query('SELECT id,owner_id FROM threads WHERE archived_at IS NULL');
  assert.equal(active.rows.length, 1);
  const {id: thread, owner_id: owner} = active.rows[0];
  await db.query(
    'INSERT INTO messages (id,owner_id,thread_id,role,text) VALUES ($1,$2,$3,$4,$5),($6,$2,$3,$7,$8)',
    [ids[0], owner, thread, 'user', messages[0], ids[1], 'assistant', messages[1]],
  );

  return {
    vaultId: saved.id, scheduleId: schedule.id, runAt, modelId: model.id,
    connectorId: connector.connectionId, connectorAccountId: connector.accountId,
    artifactId: upload.id, messageIds: ids, secrets: fingerprint(secrets),
    options: fingerprint(readFileSync('/data/options.json')),
  };
}

async function verify(expected) {
  assert.equal(fingerprint(secrets), expected.secrets, 'persistent keys');
  assert.equal(fingerprint(readFileSync('/data/options.json')), expected.options, 'Supervisor options');
  const session = await json('/api/session');
  assert.equal(session.settings.theme, 'dark');
  assert.equal(session.settings.usageData, false);
  const memoryExport = await request('/api/memory/export');
  assert.ok((await memoryExport.text()).includes(memory), 'saved memory note');

  const history = await json('/api/messages');
  for (const [index, id] of expected.messageIds.entries()) {
    const message = history.messages.find(row => row.id === id);
    assert.equal(message?.text, messages[index], 'saved message');
  }
  const data = await request('/api/artifacts/' + expected.artifactId);
  assert.match(data.headers.get('content-disposition') || '', /migration\.md/);
  assert.equal(await data.text(), artifact);

  const entries = await json('/api/vault');
  assert.equal(entries.find(row => row.id === expected.vaultId)?.label, vaultLabel);
  const revealed = await json('/api/vault/' + expected.vaultId + '/password', 'POST', {});
  assert.ok(revealed.password === vaultPassword, 'existing vault secret decrypts');

  const schedules = await json('/api/schedules');
  const schedule = schedules.find(row => row.id === expected.scheduleId);
  assert.equal(schedule?.title, scheduleTitle);
  assert.equal(schedule.prompt, schedulePrompt);
  assert.equal(schedule.enabled, false);
  assert.equal(new Date(schedule.runAt).toISOString(), expected.runAt);

  const models = await json('/api/models');
  const model = models.connections.find(row => row.id === expected.modelId);
  assert.ok(model?.models.some(choice => choice.id === modelName), 'existing model is listed');
  const previousReads = authenticatedModelReads;
  await json('/api/models/connections/' + expected.modelId + '/refresh', 'POST');
  assert.ok(authenticatedModelReads > previousReads, 'existing model credential authenticates');

  const connectors = await json('/api/apps');
  const connector = connectors.find(row => row.connectionId === expected.connectorId);
  assert.equal(connector?.accountId, expected.connectorAccountId);
  assert.equal(connector.accountName, connectorAccount);
  assert.equal(connector.status, 'connected');
  assert.ok(connector.accessPaths.some(path => path.kind === 'mcp' && path.endpoint === fixtureOrigin + '/mcp'));
  // Read the persisted grant with Nod's own crypto, then use it to list the fixture's tools.
  const grants = await db.query('SELECT owner_id,ciphertext FROM vault_app_grants WHERE id=$1', [expected.connectorId]);
  assert.equal(grants.rows.length, 1);
  const grant = grants.rows[0];
  const key = openVaultValue(Buffer.from(vaultKey, 'base64'), ['nod-app-grant-v1', grant.owner_id, expected.connectorId], grant.ciphertext);
  assert.ok(key === mcpKey, 'existing MCP grant decrypts');
  const transport = createDiscoveredTransport(ownerFetch(fixtureOrigin));
  const {tools} = await transport.listTools(fixtureOrigin + '/mcp', {Authorization: 'Bearer ' + key});
  assert.deepEqual(tools.map(tool => tool.name), ['ci_read_marker']);
}

try {
  if (mode === 'seed') {
    const expected = await seed();
    await verify(expected);
    console.log(JSON.stringify(expected));
  } else {
    await verify(JSON.parse(snapshot));
    console.log('NOD_SYNTHETIC_MIGRATION_FIXTURES_OK');
  }
} finally {
  await db.end();
  await new Promise((resolve, reject) => fixture.close(error => error ? reject(error) : resolve()));
}
