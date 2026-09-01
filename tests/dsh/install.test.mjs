import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {root} from './dsh-test-helpers.mjs';

test('npm package declares a valid dsh bundle', async () => {
  const pkg = JSON.parse(await readFile(`${root}/package.json`));
  assert.equal(pkg.name, 'misakanet');
  assert.match(pkg.version, /^\d+\.\d+\.\d+$/);
  assert.equal(pkg.dsh.bundle.patch, './cordis.patch.yml');
  assert.equal(pkg.dsh.client.platform, 'web');
});

test('all supported installation entry points are documented', async () => {
  const readme = await readFile(`${root}/README.md`, 'utf8');
  for (const command of ['dsh plugin add misakanet', 'git+https://github.com/Ikalus1988/MisakaNet.git']) assert.match(readme, new RegExp(command.replace(/[.+]/g, '\\$&')));
});
