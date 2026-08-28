// PRD ④ tests: D1 lesson service — worker prefers D1 when bound, falls back
// to GitHub (KV cache) when not. Verifies both search and /api/lessons.
// Run: node --test workers/d1-lesson-service.test.mjs
import assert from 'node:assert/strict';
import test from 'node:test';
import worker from './register-proxy-sw.js';

const TOKEN = 'd1-test-token';

// Minimal D1 stub: prepare().all() returns rows from an in-memory array.
function createD1(rows) {
  return {
    prepare() {
      return { all: async () => ({ results: rows }) };
    },
  };
}

function createKV(seed = {}) {
  const store = new Map(Object.entries(seed));
  return {
    async get(key, type) {
      if (!store.has(key)) return null;
      const raw = store.get(key);
      return type === 'json' ? JSON.parse(raw) : raw;
    },
    async put(key, value) {
      store.set(key, value);
    },
    _store: store,
  };
}

const D1_ROWS = [
  {
    id: 'd1-pip-mirror',
    title: 'pip install timeout (from D1)',
    domain: 'python',
    status: 'published',
    tags: '["pip","network"]',
    path: 'lessons/core/d1-pip-mirror.md',
    summary: 'Use a mirror for pip timeouts.',
    problem: 'pip install times out.',
    updated: '2026-08-28T00:00:00Z',
    created: '2026-06-01T00:00:00Z',
  },
  {
    id: 'd1-dco',
    title: 'DCO sign-off (from D1)',
    domain: 'git',
    status: 'published',
    tags: '["github","dco"]',
    path: 'lessons/core/d1-dco.md',
    summary: 'GitHub requires sign-off.',
    problem: 'DCO check failed.',
    updated: '2026-08-27T00:00:00Z',
    created: '2026-06-02T00:00:00Z',
  },
];

function mcpSearch(query, env) {
  return worker.fetch(new Request('https://misakanet.org/mcp', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      'Content-Type': 'application/json',
      'MCP-Protocol-Version': '2025-06-18',
      'CF-Connecting-IP': '203.0.113.7',
    },
    body: JSON.stringify({
      jsonrpc: '2.0', id: 1, method: 'tools/call',
      params: { name: 'misakanet_search', arguments: { query } },
    }),
  }), env);
}

async function resultText(response) {
  const body = await response.json();
  return JSON.parse(body.result.content[0].text);
}

test('misakanet_search uses D1 rows when MISAKANET_D1 is bound', async () => {
  const env = {
    MCP_TOKEN: TOKEN,
    MISAKANET_D1: createD1(D1_ROWS),
    MISAKANET_KV: createKV(),
  };
  const resp = await mcpSearch('pip install timeout', env);
  assert.equal(resp.status, 200);
  const result = await resultText(resp);
  assert.ok(result.results.length >= 1);
  assert.equal(result.results[0].id, 'd1-pip-mirror');
  assert.match(result.results[0].title, /from D1/);
});

test('/api/lessons returns D1 rows when bound, with no REGISTER_TOKEN needed', async () => {
  const env = { MISAKANET_D1: createD1(D1_ROWS) };
  const resp = await worker.fetch(new Request('https://misakanet.org/api/lessons'), env);
  assert.equal(resp.status, 200);
  const data = await resp.json();
  assert.ok(Array.isArray(data));
  assert.equal(data.length, 2);
  assert.equal(data[0].id, 'd1-pip-mirror');
  assert.deepEqual(data[0].tags, ['pip', 'network']);
});

test('falls back to GitHub/KV cache when D1 is not bound', async () => {
  const lessons = [
    { id: 'gh-lesson', title: 'GitHub lesson', domain: 'devops', description: 'from github' },
  ];
  const env = {
    MCP_TOKEN: TOKEN,
    MISAKANET_KV: createKV({
      'proxy:lessons': JSON.stringify({ ts: Date.now(), data: lessons }),
    }),
  };
  const resp = await mcpSearch('GitHub lesson', env);
  assert.equal(resp.status, 200);
  const result = await resultText(resp);
  assert.equal(result.results[0].id, 'gh-lesson');
});

test('falls back to GitHub when D1 is bound but empty', async () => {
  const lessons = [
    { id: 'gh-fallback', title: 'GitHub fallback lesson', domain: 'devops', description: 'fallback' },
  ];
  const env = {
    MCP_TOKEN: TOKEN,
    MISAKANET_D1: createD1([]),
    MISAKANET_KV: createKV({
      'proxy:lessons': JSON.stringify({ ts: Date.now(), data: lessons }),
    }),
  };
  const resp = await mcpSearch('fallback lesson', env);
  const result = await resultText(resp);
  assert.equal(result.results[0].id, 'gh-fallback');
});
