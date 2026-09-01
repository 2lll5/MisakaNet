# DeepSeekHarness (dsh) integration

MisakaNet can be installed into dsh as a skill/plugin. The bundle provides failure-memory guidance through `SKILL.md`; it does not start a background service.

## Install

```bash
dsh plugin add misakanet
```

Alternative GitHub source:

```bash
dsh plugin add github:Ikalus1988/MisakaNet
```

For environments without the plugin manager, use [manual skill discovery](../dsh-installation.md#3-manual-skill-discovery) or configure the [MCP adapter](../integration/deepseek-harness.md).

## Check and remove

```bash
dsh plugin list
dsh plugin remove misakanet
```

See the [full installation guide](../dsh-installation.md) for prerequisites and troubleshooting.