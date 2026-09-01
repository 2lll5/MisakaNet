import test from 'node:test';
import assert from 'node:assert/strict';
import {request} from './dsh-test-helpers.mjs';

test('MCP compatibility contract exposes standard discovery methods', async () => {
  const init = await request('initialize');
  assert.equal(init.jsonrpc, '2.0');
  assert.ok(init.result.protocolVersion);
  const resources = await request('resources/list');
  assert.ok(resources.result.resources.some(item => item.uri === 'misaka://lessons/index'));
});

test('unknown methods use JSON-RPC method-not-found errors', async () => {
  const response = await request('method/does-not-exist');
  assert.equal(response.error.code, -32601);
});
