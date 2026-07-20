#!/usr/bin/env python3
"""Node status dashboard — read MisakaNet KV to display node stats.

Usage:
    # Via wrangler (requires Cloudflare auth)
    python3 scripts/node_status.py

    # Or pass KV namespace ID directly
    python3 scripts/node_status.py --kv-id d5fb6b0797b84d17b0586fb982231ffe

Output:
    Node Counter: 10060
    Latest Node ID: Misaka00060
    Active Nodes (sampled): 5
"""
import argparse
import json
import subprocess
import sys


def run_wrangler(command: str, kv_id: str = None) -> str:
    """Run a wrangler KV command and return stdout."""
    cmd = ["npx", "wrangler", "kv", "key"]
    cmd.extend(command.split())
    if kv_id:
        cmd.extend(["--namespace-id", kv_id])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return ""
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def main():
    parser = argparse.ArgumentParser(description="MisakaNet node status dashboard")
    parser.add_argument("--kv-id", help="KV namespace ID", default=None)
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    kv_id = args.kv_id or "d5fb6b0797b84d17b0586fb982231ffe"

    # Get node_counter
    counter_raw = run_wrangler(f"get node_counter", kv_id)
    counter = int(counter_raw) if counter_raw and counter_raw.isdigit() else None

    # Calculate latest node ID
    latest_id = f"Misaka{str(counter).zfill(5)}" if counter else "unknown"

    # Sample some recent nodes (check last 10 IDs)
    active_nodes = []
    if counter:
        for i in range(max(0, counter - 9), counter + 1):
            node_id = f"Misaka{str(i).zfill(5)}"
            node_data = run_wrangler(f'get "node:{node_id}"', kv_id)
            if node_data:
                try:
                    info = json.loads(node_data)
                    active_nodes.append({
                        "nodeId": info.get("nodeId", node_id),
                        "source": info.get("source", "?"),
                        "registeredAt": info.get("registeredAt", "?")[:10],
                    })
                except json.JSONDecodeError:
                    active_nodes.append({"nodeId": node_id, "source": "?", "registeredAt": "?"})

    if args.json:
        print(json.dumps({
            "counter": counter,
            "latest_node_id": latest_id,
            "active_nodes_sample": active_nodes,
            "active_count": len(active_nodes),
        }, ensure_ascii=False, indent=2))
    else:
        print(f"Node Counter:    {counter or 'unknown'}")
        print(f"Latest Node ID:  {latest_id}")
        print(f"Active (sampled): {len(active_nodes)}/10")
        if active_nodes:
            print()
            print("Recent nodes:")
            for n in active_nodes:
                print(f"  {n['nodeId']}  source={n['source']}  registered={n['registeredAt']}")


if __name__ == "__main__":
    main()
