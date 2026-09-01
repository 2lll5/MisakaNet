# MisakaNet dsh Plugin Installation

This guide installs MisakaNet as a [DeepSeekHarness (dsh)](https://github.com/Ikalus1988/MisakaNet) plugin. The plugin bundles `SKILL.md`; its MCP adapter remains available for harnesses that use stdio MCP directly.

## Prerequisites

- `dsh` with plugin support (`dsh --version`); use a current release.
- Node.js 18 or newer (`node --version`).
- Network access to the dsh marketplace or GitHub for the first two methods.
- A writable home directory for `~/.dsh/` when using manual discovery.

## Installation methods

### 1. dsh plugin marketplace (recommended)

```bash
dsh plugin add misakanet
```

### 2. GitHub installation

```bash
dsh plugin add github:Ikalus1988/MisakaNet
```

### 3. Manual skill discovery

From a checkout of this repository:

```bash
mkdir -p ~/.dsh/skills
cp -r skills/misakanet ~/.dsh/skills/
```

If this checkout does not contain `skills/misakanet`, copy the repository skill bundle instead:

```bash
mkdir -p ~/.dsh/skills/misakanet
cp SKILL.md ~/.dsh/skills/misakanet/
```

## Verification

For marketplace or GitHub installation, confirm the plugin is listed:

```bash
dsh --version
dsh plugin list
```

The list should contain `misakanet`. For manual discovery, verify the skill file:

```bash
test -s ~/.dsh/skills/misakanet/SKILL.md && echo "misakanet skill discovered"
```

To verify the MCP adapter independently:

```bash
python3 -m py_compile scripts/mcp_deepseek_adapter.py scripts/mcp_server.py
python3 scripts/mcp_deepseek_adapter.py --help
```

## Troubleshooting

### Permission denied

Make the user-owned dsh directory and copy as the same user that runs dsh:

```bash
mkdir -p "$HOME/.dsh/skills"
```

Do not use `sudo` unless dsh itself is installed system-wide.

### Plugin is not listed

Check the command spelling and update dsh. For a GitHub install, check network access and retry with the full repository reference. For manual discovery, ensure the file is exactly `~/.dsh/skills/misakanet/SKILL.md` and restart dsh.

### Node.js or version conflict

Check `node --version` and use Node.js 18+. The plugin is a skill bundle and does not require a separate Node runtime after installation, but dsh's plugin manager may require Node.js while resolving packages.

### Network failure

Use the manual method from a local checkout, or run the adapter directly:

```bash
python3 scripts/mcp_deepseek_adapter.py
```

## Uninstallation

Remove a managed plugin with:

```bash
dsh plugin remove misakanet
```

Remove a manually discovered skill with:

```bash
rm -rf ~/.dsh/skills/misakanet
```

Then restart dsh and confirm it no longer appears in `dsh plugin list`.

## Related documentation

- [DeepSeekHarness integration](integration/deepseek-harness.md)
- [MCP quickstart](mcp-quickstart.md)