import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

export const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');

const python = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
const pending = new Map();
let child;
let nextId = 1;
let buffered = '';
let idleTimer;

function stopServer() {
  if (!child) return;
  child.kill();
  child = undefined;
  buffered = '';
}

function scheduleStop() {
  clearTimeout(idleTimer);
  if (pending.size !== 0) return;
  idleTimer = setTimeout(stopServer, 1000);
  idleTimer.unref();
}

function startServer() {
  if (child) return;
  child = spawn(python, ['-u', 'scripts/mcp_server.py'], {cwd: root});
  child.stdout.setEncoding('utf8');
  child.stdout.on('data', chunk => {
    buffered += chunk;
    const lines = buffered.split(/\r?\n/);
    buffered = lines.pop();
    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const response = JSON.parse(line);
        const entry = pending.get(response.id);
        if (entry) {
          pending.delete(response.id);
          clearTimeout(entry.timer);
          entry.resolve(response);
          scheduleStop();
        }
      } catch {
        // Ignore non-JSON diagnostic output; protocol responses are JSON lines.
      }
    }
  });
  const fail = error => {
    for (const entry of pending.values()) {
      clearTimeout(entry.timer);
      entry.reject(error);
    }
    pending.clear();
    child = undefined;
    buffered = '';
  };
  child.on('error', fail);
  child.on('close', code => fail(new Error(`MCP server exited with code ${code}`)));
}

export function request(method, params = {}, id = nextId++) {
  startServer();
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(id);
      reject(new Error(`timeout waiting for ${method}`));
    }, 15000);
    pending.set(id, {resolve, reject, timer});
    child.stdin.write(JSON.stringify({jsonrpc: '2.0', id, method, params}) + '\n');
  });
}

process.on('exit', () => child?.kill());

export function toolResult(response) {
  const text = response?.result?.content?.find(item => item.type === 'text')?.text;
  return text ? JSON.parse(text) : response;
}
