# VaultAnchorWrite.v1 — HTTP API Specification

**Endpoint**: `POST /vault/anchor/write`  
**Version**: `1.0.0`  
**Content-Type**: `application/json`

---

## Purpose

Fossilize an artifact into the Vault. Returns a sealed, signed receipt that serves as cryptographic proof of immutability.

---

## Request Schema

```json
{
  "schema_version": "VaultAnchorWriteRequest.v1",
  "artifact_kind": "<string>",
  "payload_hash_sha256": "<hex-64>",
  "run_id": "<string>",
  "operator": "<string>",
  "ts": "<ISO-8601>"
}
```

| Field                 | Type   | Required | Description                                                 |
|-----------------------|--------|----------|-------------------------------------------------------------|
| `schema_version`      | string | ✓        | Must be `"VaultAnchorWriteRequest.v1"`                      |
| `artifact_kind`       | string | ✓        | Schema name of the artifact (e.g., `"InferenceReceipt.v1"`) |
| `payload_hash_sha256` | string | ✓        | Lowercase hex SHA-256 of the canonical payload (64 chars)   |
| `run_id`              | string | ✓        | Unique identifier for the run/session                       |
| `operator`            | string | ✓        | Identity of the operator/agent                              |
| `ts`                  | string | ✓        | ISO-8601 timestamp of artifact creation                     |

### Example Request

```json
{
  "schema_version": "VaultAnchorWriteRequest.v1",
  "artifact_kind": "InferenceReceipt.v1",
  "payload_hash_sha256": "6a47c1eee539c79b6ed05d4766d01831099c4043dab1431aa3a9b82018b80e7b",
  "run_id": "run-2026-01-20-001",
  "operator": "earl",
  "ts": "2026-01-20T20:40:00Z"
}
```

---

## Response Schema

**Success**: `200 OK`

```json
{
  "schema_version": "VaultFossilizationReceipt.v1",
  "artifact_kind": "<string>",
  "payload_hash": "<hex-64>",
  "vault_fingerprint": "<hex-64>",
  "anchor_id": "<uuid>",
  "anchor_hash": "<hex-64>",
  "ts": "<ISO-8601>",
  "sealed": true,
  "signature": "<base64>"
}
```

| Field               | Type    | Description                                                    |
|---------------------|---------|----------------------------------------------------------------|
| `schema_version`    | string  | Always `"VaultFossilizationReceipt.v1"`                        |
| `artifact_kind`     | string  | Echoed from request                                            |
| `payload_hash`      | string  | Echoed from request                                            |
| `vault_fingerprint` | string  | SHA-256 of Vault's public key                                  |
| `anchor_id`         | string  | UUID assigned by Vault                                         |
| `anchor_hash`       | string  | SHA-256 of the receipt's JCS bytes (before this field is set)  |
| `ts`                | string  | Timestamp of fossilization                                     |
| `sealed`            | boolean | Always `true` on success                                       |
| `signature`         | string  | Ed25519 signature over pre-anchor JCS bytes                    |

### Example Response

```json
{
  "schema_version": "VaultFossilizationReceipt.v1",
  "artifact_kind": "InferenceReceipt.v1",
  "payload_hash": "6a47c1eee539c79b6ed05d4766d01831099c4043dab1431aa3a9b82018b80e7b",
  "vault_fingerprint": "b845ab76aee9d2956a0aa82a82a82a82a82a82a82a82a82a82a82a82a82a82a8",
  "anchor_id": "f7b9c2d4-1e3a-4b5c-8d9e-001122334455",
  "anchor_hash": "33c2b24ef2f42a26babcadeafe1cece8ed8f0cc15033df825942402bb023c302",
  "ts": "2026-01-20T20:40:06Z",
  "sealed": true,
  "signature": "MEQCIDF1vXq3u3u3u3u3u3u3u3u3u3u3u3u3u3u3u3u3u3AiBq7p7p0pVqCqgqgqgqgqgqgqgqgqgqgqgqgqg=="
}
```

---

## Error Surface

All errors return JSON with this structure:

```json
{
  "error": "<error_code>",
  "message": "<human_readable>",
  "details": {}
}
```

| HTTP  | Error Code                | Cause                                           |
|-------|---------------------------|-------------------------------------------------|
| `400` | `INVALID_SCHEMA_VERSION`  | `schema_version` missing or unsupported         |
| `400` | `INVALID_PAYLOAD_HASH`    | `payload_hash_sha256` not 64 hex chars          |
| `400` | `MISSING_REQUIRED_FIELD`  | Required field missing                          |
| `400` | `INVALID_TIMESTAMP`       | `ts` not valid ISO-8601                         |
| `409` | `DUPLICATE_ANCHOR`        | `payload_hash_sha256` already fossilized        |
| `422` | `CANONICALIZATION_FAILED` | Request body not valid JSON or not JCS-sortable |
| `500` | `SIGNING_FAILED`          | Vault key unavailable or signing error          |
| `503` | `VAULT_UNAVAILABLE`       | Vault temporarily offline                       |

### Example Error

```json
{
  "error": "INVALID_PAYLOAD_HASH",
  "message": "payload_hash_sha256 must be 64 lowercase hex characters",
  "details": {
    "received": "6a47c1",
    "expected_length": 64
  }
}
```

---

## Caller Invariants

### MUST

| # | Invariant |
| - | - |
| 1 | Caller **MUST** compute `payload_hash_sha256` as `sha256(JCS(payload))` — the hash of the JCS-canonicalized payload bytes. |
| 2 | Caller **MUST** use lowercase hex encoding for all hashes. |
| 3 | Caller **MUST** use ISO-8601 format with `Z` suffix for `ts`. |
| 4 | Caller **MUST** retain the original payload locally — the Vault does not store it. |
| 5 | Caller **MUST** verify the returned `signature` against the Vault's public key before trusting the receipt. |
| 6 | Caller **MUST** verify that `anchor_hash == sha256(JCS(receipt_without_anchor_hash))`. |

### MUST NOT

| # | Invariant |
| - | - |
| 1 | Caller **MUST NOT** submit the same `payload_hash_sha256` twice — duplicates are rejected with `409`. |
| 2 | Caller **MUST NOT** modify the receipt after receiving it — any modification invalidates the signature. |
| 3 | Caller **MUST NOT** assume `anchor_id` format — treat as opaque string. |
| 4 | Caller **MUST NOT** send non-JCS-canonical JSON — use sorted keys, no whitespace. |

---

## Canonicalization Rules

All JSON in this protocol follows **JCS (RFC 8785)**:

1. Keys sorted lexicographically (Unicode code point order)
2. No insignificant whitespace
3. Numbers as shortest decimal representation
4. Strings escaped per JSON spec

### Hash Computation

```python
payload_hash_sha256 = sha256(JCS(payload)).hex().lower()
anchor_hash         = sha256(JCS(receipt_before_anchor_hash)).hex().lower()
```

---

## Signature Contract

The Vault signs the **pre-anchor receipt** — the receipt with `anchor_id` populated but `anchor_hash` set to empty string `""`.

```python
message = JCS({
  ...receipt,
  "anchor_hash": "",
  "sealed": true
})

signature = Ed25519.sign(vault_private_key, message)
```

### Verification

```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

message = jcs_canonicalize(receipt_with_anchor_hash_empty)
vault_pubkey = Ed25519PublicKey.from_public_bytes(vault_public_key_bytes)
vault_pubkey.verify(signature_bytes, message)
```

---

## Replay-Court Reconstruction

Given a `VaultFossilizationReceipt.v1`, any party can:

1. Obtain the original payload from the caller's archive
2. Compute `sha256(JCS(payload))` → must equal `payload_hash`
3. Reconstruct pre-anchor JCS bytes
4. Verify Ed25519 signature against Vault's public key
5. Compute `sha256(JCS(receipt_before_anchor_hash))` → must equal `anchor_hash`

If all checks pass, the receipt is **admissible** as proof of fossilization at time `ts`.

---

## Ledger Line Format

After successful fossilization, the Vault appends a line to its immutable ledger:

```json
{"schema_version":"VaultLedgerLine.v1","anchor_id":"...","anchor_hash":"...","artifact_kind":"...","payload_hash":"...","run_id":"...","ts":"...","vault_fingerprint":"...","signature":"..."}
```

This line is append-only and never modified.

---

## Version History

| Version | Date       | Changes               |
|---------|------------|-----------------------|
| 1.0.0   | 2026-01-20 | Initial specification |
