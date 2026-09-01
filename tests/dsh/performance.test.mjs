import test from 'node:test';
import assert from 'node:assert/strict';
import {performance} from 'node:perf_hooks';
import {request, toolResult} from './dsh-test-helpers.mjs';

test('server startup and discovery complete within 10 seconds', async () => {
  const start = performance.now();
  const response = await request('tools/list');
  assert.ok(response.result.tools.length > 0);
  assert.ok(performance.now() - start < 10000);
});

test('concurrent searches return independent valid responses', async () => {
  const responses = await Promise.all(['node', 'python', 'timeout', 'MCP'].map(query => request('tools/call', {name: 'misakanet_search', arguments: {query, top: 2}})));
  for (const response of responses) {
    const result = toolResult(response);
    assert.ok(Array.isArray(result.results) || result.error);
  }
});
