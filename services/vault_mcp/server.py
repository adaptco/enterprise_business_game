#!/usr/bin/env python3
"""
VaultAnchorWrite MCP Server
Exposes write_vault_anchor tool via Model Context Protocol (stdio).
"""

import json
import sys
from vault import Vault


def handle_request(request: dict) -> dict:
    """Handle a single JSON-RPC request."""
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "vault-anchor-write",
                    "version": "1.0.0"
                }
            }
        }
    
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "write_vault_anchor",
                        "description": "Fossilize an artifact into the Vault. Returns a signed receipt.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "artifact_kind": {"type": "string", "description": "Schema name of artifact"},
                                "payload_hash_sha256": {"type": "string", "description": "SHA-256 of canonical payload (64 hex)"},
                                "run_id": {"type": "string", "description": "Unique run identifier"},
                                "operator": {"type": "string", "description": "Operator identity"},
                                "ts": {"type": "string", "description": "ISO-8601 timestamp"}
                            },
                            "required": ["artifact_kind", "payload_hash_sha256", "run_id", "operator", "ts"]
                        }
                    }
                ]
            }
        }
    
    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        
        if tool_name == "write_vault_anchor":
            try:
                vault = Vault()
                receipt = vault.write_anchor(
                    artifact_kind=args.get("artifact_kind", ""),
                    payload_hash_sha256=args.get("payload_hash_sha256", ""),
                    run_id=args.get("run_id", ""),
                    operator=args.get("operator", ""),
                    ts=args.get("ts", "")
                )
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(receipt, indent=2)}]
                    }
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Error: {e}"}],
                        "isError": True
                    }
                }
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code":-32601, "message": f"Unknown tool: {tool_name}"}
            }
    
    elif method == "notifications/initialized":
        return None  # No response for notifications
    
    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code":-32601, "message": f"Unknown method: {method}"}
        }


def main():
    """MCP server main loop — reads JSON-RPC from stdin, writes to stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        try:
            request = json.loads(line)
            response = handle_request(request)
            if response:
                print(json.dumps(response), flush=True)
        except json.JSONDecodeError as e:
            err = {"jsonrpc": "2.0", "id": None, "error": {"code":-32700, "message": f"Parse error: {e}"}}
            print(json.dumps(err), flush=True)


if __name__ == "__main__":
    main()
