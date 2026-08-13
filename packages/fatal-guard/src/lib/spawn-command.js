/**
 * Build a shell-free child-process invocation for Unix and Windows.
 *
 * Windows `.cmd`/`.bat` files are not directly executable with CreateProcess.
 * Routing only those extensions through ComSpec keeps normal commands on the
 * safe direct-spawn path while preserving PATH lookup for PowerShell/cmd
 * workflows used by the CLI.
 */

function quoteWindowsArg(value) {
  const text = String(value);
  if (!/[\s"&|<>^]/.test(text)) return text;
  return `"${text.replace(/["^]/g, (match) => `^${match}`)}"`;
}

function buildSpawnSpec(command, args = []) {
  const isWindowsScript = process.platform === 'win32' && /\.(?:cmd|bat)$/i.test(command);
  if (!isWindowsScript) {
    return { command, args, options: {} };
  }
  const shellCommand = [command, ...args].map(quoteWindowsArg).join(' ');
  return {
    command: process.env.ComSpec || 'cmd.exe',
    args: ['/d', '/s', '/c', shellCommand],
    options: { windowsHide: true },
  };
}

module.exports = { buildSpawnSpec, quoteWindowsArg };
