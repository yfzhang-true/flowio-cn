"""Call an MCP tool on mcp-lootdrop via stdio and print the result JSON.

Usage: python lootdrop_call.py <tool_name> [json_arguments]
"""
import json
import subprocess
import sys

NPX = r"C:\Program Files\nodejs\npx.cmd"


def main() -> int:
    tool = sys.argv[1] if len(sys.argv) > 1 else "lootdrop_diagnose"
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}

    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "cli", "version": "1.0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
            "name": tool, "arguments": args}},
    ]
    payload = "\n".join(json.dumps(m) for m in messages) + "\n"
    proc = subprocess.run(
        [NPX, "-y", "mcp-lootdrop"], input=payload.encode(),
        capture_output=True, timeout=120,
    )
    out = proc.stdout.decode("utf-8", errors="replace")
    result = None
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("id") == 2:
            result = obj
    if result is None:
        print("NO RESULT. stdout:", out[:800])
        print("stderr:", proc.stderr.decode("utf-8", errors="replace")[:500])
        return 1
    content = result.get("result", {}).get("content", [])
    for block in content:
        if block.get("type") == "text":
            print(block["text"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
