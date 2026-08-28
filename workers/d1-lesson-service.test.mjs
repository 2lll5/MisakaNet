// PRD ④ tests: D1 lesson service — worker prefers D1 when bound, falls back
// to GitHub (KV cache) when not. Verifies search, /api/lessons, get_lesson.
// Run: node --test workers/d1-lesson-service.test.mjs
import assert from 'node:assert/strict';
import test from 'node:test';
import worker from './register-proxy-sw.js';

const TOKEN = 'd1-test-token';

// D1 stub: prepare(sql).bind(...).all() filters the in-memory rows for the
// two query shapes used by the worker (full scan / WHERE path= / WHERE id=).
function createD1(rows) {
  return {
    prepare(sql) {
      const matcher = sql.includes('WHERE path = ?1')
        ? (bound) => rows.filter((r) => r.path === bound[0])
        : sql.includes('WHERE id = ?1')
          ? (bound) => rows.filter((r) => r.id === bound[0])
          : () => rows;
      const stmt = {
        bind(...args) {
          stmt._bound = args;
          return stmt;
        },
        async all() {
          return { results: matcher(stmt._bound || []) };
        },
      };
      return stmt;
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

// ── get_lesson via D1 (PRD ④ §3.3) ──

const D1_FULL = D1_ROWS.map((r) => ({ ...r, content_md: `# ${r.title}\n\nFull body for ${r.id}.` }));

function mcpGetLesson(args, env) {
  return worker.fetch(new Request('https://misakanet.org/mcp', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      'Content-Type': 'application/json',
      'MCP-Protocol-Version': '2025-06-18',
      'CF-Connecting-IP': '203.0.113.8',
    },
    body: JSON.stringify({
      jsonrpc: '2.0', id: 1, method: 'tools/call',
      params: { name: 'misakanet_get_lesson', arguments: args },
    }),
  }), env);
}

test('misakanet_get_lesson returns full content from D1 by path', async () => {
  const env = { MCP_TOKEN: TOKEN, MISAKANET_D1: createD1(D1_FULL), MISAKANET_KV: createKV() };
  const resp = await mcpGetLesson({ path: 'lessons/core/d1-pip-mirror.md' }, env);
  assert.equal(resp.status, 200);
  const result = await resultText(resp);
  assert.equal(result.path, 'lessons/core/d1-pip-mirror.md');
  assert.match(result.content, /Full body for d1-pip-mirror/);
});

test('misakanet_get_lesson returns full content from D1 by id', async () => {
  const env = { MCP_TOKEN: TOKEN, MISAKANET_D1: createD1(D1_FULL), MISAKANET_KV: createKV() };
  const resp = await mcpGetLesson({ id: 'd1-dco' }, env);
  assert.equal(resp.status, 200);
  const result = await resultText(resp);
  assert.match(result.content, /Full body for d1-dco/);
});

test('misakanet_get_lesson falls back to GitHub when D1 has no row', async () => {
  // D1 bound but no matching row → fetchLessonFromD1 returns null → GitHub path.
  // GitHub will 401 without REGISTER_TOKEN, proving we attempted the fallback.
  const env = { MCP_TOKEN: TOKEN, MISAKANET_D1: createD1([]), MISAKANET_KV: createKV() };
  const resp = await mcpGetLesson({ id: 'no-such-lesson' }, env);
  const body = await resp.json();
  const text = body.result.content[0].text;
  assert.match(text, /not found|REGISTER_TOKEN|GitHub API 401/);
});
