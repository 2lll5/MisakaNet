import test from 'node:test';
import assert from 'node:assert/strict';
import {request, toolResult} from './dsh-test-helpers.mjs';

test('MCP initializes and advertises the dsh tools', async () => {
  const response = await request('initialize');
  assert.equal(response.result.serverInfo.name, 'misakanet');
  assert.ok(response.result.capabilities.tools);
  const listed = await request('tools/list');
  const names = listed.result.tools.map(tool => tool.name);
  assert.ok(names.includes('misakanet_search'));
  assert.ok(names.includes('misakanet_get_lesson'));
});

test('search discovers and fetches a lesson', async () => {
  const search = toolResult(await request('tools/call', {name: 'misakanet_search', arguments: {query: 'CI pipeline', top: 3}}));
  assert.ok(Array.isArray(search.results));
  const lesson = toolResult(await request('tools/call', {name: 'misakanet_get_lesson', arguments: {path: 'lessons/ru/shell-script-debugging.md'}}));
  assert.ok(lesson.content?.length > 10);
});

test('lesson index resource is readable', async () => {
  const response = await request('resources/read', {uri: 'misaka://lessons/index'});
  const text = response.result.contents?.[0]?.text;
  assert.ok(text);
  const index = JSON.parse(text);
  assert.ok(index.count >= 0 && Array.isArray(index.lessons));
});

test('invalid tool input returns a structured error', async () => {
  const result = toolResult(await request('tools/call', {name: 'misakanet_search', arguments: {}}));
  assert.equal(result.error, 'query is required');
});
