# VaultAnchorWrite MCP Server

MCP server exposing the `VaultAnchorWrite.v1` API as a tool for Agents.

## Quick Start

```bash
cd services/vault_mcp
python server.py
```

The server reads JSON-RPC from stdin and writes responses to stdout.

---

## Tool: `write_vault_anchor`

Fossilize an artifact into the Vault. Returns a signed `VaultFossilizationReceipt.v1`.

### Input Schema

```json
{
  "artifact_kind": "InferenceReceipt.v1",
  "payload_hash_sha256": "6a47c1eee539c79b6ed05d4766d01831099c4043dab1431aa3a9b82018b80e7b",
  "run_id": "run-2026-01-20-001",
  "operator": "earl",
  "ts": "2026-01-20T20:40:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `artifact_kind` | string | Schema name of the artifact |
| `payload_hash_sha256` | string | SHA-256 of canonical payload (64 lowercase hex) |
| `run_id` | string | Unique run identifier |
| `operator` | string | Operator identity |
| `ts` | string | ISO-8601 timestamp |

### Output

```json
{
  "schema_version": "VaultFossilizationReceipt.v1",
  "artifact_kind": "InferenceReceipt.v1",
  "payload_hash": "6a47c1eee539c79b6ed05d4766d01831099c4043dab1431aa3a9b82018b80e7b",
  "vault_fingerprint": "b845ab76aee9d2956a0aa82a82a82a82a82a82a82a82a82a82a82a82a82a82a8",
  "anchor_id": "f7b9c2d4-1e3a-4b5c-8d9e-001122334455",
  "anchor_hash": "33c2b24ef2f42a26babcadeafe1cece8ed8f0cc15033df825942402bb023c302",
  "ts": "2026-01-28T06:50:00Z",
  "sealed": true,
  "signature": "MEQCIDF1..."
}
```

---

## Tool: `deploy_tensor_slice`

Deploy a tensor slice (checkpoint) into a LÖVE game package.

### Input Schema

```json
{
  "slice_path": "checkpoints/hawthorne_checkpoint.v1.json",
  "output_path": "dist/hawthorne_deploy.love"
}
```

### Output

Returns success message with stdout from the deployer script.

---

## MCP Client Configuration

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "vault": {
      "command": "python",
      "args": ["C:/path/to/services/vault_mcp/server.py"]
    }
  }
}
```

### VS Code / Other Agents

Configure the MCP client to spawn `python server.py` via stdio.

---

## Spec Reference

See [`docs/VaultAnchorWrite.v1.md`](../../docs/VaultAnchorWrite.v1.md) for the full HTTP API specification.

---

## Files

| File | Description |
|------|-------------|
| `server.py` | MCP JSON-RPC handler (stdio) |
| `vault.py` | Core vault logic (JCS, hashing, signing) |
| `requirements.txt` | Dependencies (stdlib only) |

---

## Test

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python server.py
```

Expected: JSON with `write_vault_anchor` tool definition.
