# Unified Tensor Runtime Block Specification

## Overview

The **Unified Tensor Runtime Block** is an encapsulated configuration container that:
- Embeds runtime configurations into semantic tensor space
- Maintains Merkle-chained integrity for audit trails
- Supports multiple config sources (IPFS, local, external)
- Binds to SSOT capsules for deterministic replay

---

## Schema Location

**File:** [`schemas/unified_tensor_runtime_block.v1.schema.json`](file:///C:/Users/eqhsp/.gemini/antigravity/scratch/enterprise_business_game/schemas/unified_tensor_runtime_block.v1.schema.json)

**Schema Version:** `tensor.runtime.v1`

---

## Block Structure

```json
{
  "block_id": "uuid",
  "schema_version": "tensor.runtime.v1",
  "timestamp": "ISO8601",
  
  "tensor_semantic": {
    "embedding_space": "cici.v1",
    "coordinates": [0.123, -0.456, 0.789, ...],
    "manifold_type": "EUCLIDEAN | SE3 | PINN | CUSTOM",
    "dimension": 16
  },
  
  "runtime_config": {
    "config_source": "IPFS | LOCAL | REGISTRY | EXTERNAL",
    "ipfs_cid": "QmExampleCID... (optional)",
    "normalized_params": { ... },
    "raw_config": { ... }
  },
  
  "capsule_bindings": [
    {
      "capsule_id": "uuid",
      "capsule_type": "sovereign_state | company_registration | ...",
      "binding_hash": "SHA-256"
    }
  ],
  
  "integrity_hash": "SHA-256 of (tensor_semantic + runtime_config + bindings)",
  "prev_block_hash": "SHA-256 of previous block (Merkle link)",
  
  "metadata": {
    "creator": "string",
    "purpose": "string",
    "tags": ["array", "of", "strings"]
  }
}
```

---

## Tensor Semantic Embedding

### Purpose

Map runtime configurations into a **semantic tensor space** for:
- Similarity search (find configs with similar behavior)
- Geometric interpolation (blend configs deterministically)
- Dimension reduction (visualize config landscapes)

### Manifold Types

| Type | Description | Use Case |
|------|-------------|----------|
| **EUCLIDEAN** | Flat vector space | Standard key-value configs |
| **SE3** | 3D rigid transforms | Vehicle/robot pose configs |
| **PINN** | Physics-informed | Neural PDE solvers |
| **CUSTOM** | User-defined | Domain-specific geometries |

### Embedding Process

1. **Extract features** from normalized config (numeric values, string hashes)
2. **Hash-based projection** (deterministic): `SHA256(config) → coordinates`
3. **Normalize** to hypersphere or manifold constraints
4. **Store** coordinates + dimension + manifold type

---

## IPFS Config Normalization

### Input: IPFS JSON

```json
{
  "Addresses": {
    "API": "/ip4/127.0.0.1/tcp/5001",
    "Gateway": "/ip4/127.0.0.1/tcp/8080",
    "Swarm": ["/ip4/0.0.0.0/tcp/4001"]
  },
  "Datastore": {
    "Type": "levelds",
    "Path": "~/.ipfs/datastore"
  },
  "Bootstrap": ["..."],
  "Identity": {
    "PeerID": "QmExamplePeerID"
  }
}
```

### Output: Normalized Params

```json
{
  "network": {
    "api": "/ip4/127.0.0.1/tcp/5001",
    "gateway": "/ip4/127.0.0.1/tcp/8080",
    "swarm": ["/ip4/0.0.0.0/tcp/4001"]
  },
  "storage": {
    "type": "levelds",
    "path": "~/.ipfs/datastore"
  },
  "bootstrap_peers": ["..."],
  "identity": {
    "PeerID": "QmExamplePeerID"
  }
}
```

**Normalization Rules:**
1. **Flatten nested objects** (max 2 levels deep)
2. **Lowercase keys** (for consistency)
3. **Extract arrays** as-is
4. **Preserve order** (for deterministic hashing)

---

## Generator API

### Initialize

```python
from runtime_block_generator import RuntimeBlockGenerator, ManifoldType

generator = RuntimeBlockGenerator(embedding_space="cici.v1")
```

### Generate from IPFS Config

```python
block = generator.generate_from_ipfs(
    ipfs_json=ipfs_config,
    ipfs_cid="QmExampleCID",
    capsule_bindings=[
        {
            "capsule_id": "123e4567-e89b-12d3-a456-426614174000",
            "capsule_type": "sovereign_state",
            "binding_hash": "a1b2c3..."
        }
    ],
    metadata={
        "creator": "my_app",
        "purpose": "IPFS node config",
        "tags": ["ipfs", "distributed"]
    }
)
```

### Generate from Local Config

```python
block = generator.generate_from_local(
    config={
        "server": {"host": "localhost", "port": 8080},
        "database": {"type": "postgres", "url": "..."}
    },
    manifold_type=ManifoldType.EUCLIDEAN,
    metadata={"creator": "my_app"}
)
```

### Verify Block

```python
# Single block
valid = generator.verify_block_integrity(block)

# Chain of blocks
valid = generator.verify_chain([block1, block2, block3])
```

---

## Merkle Chain

Each block links to the previous via `prev_block_hash`:

```
Genesis Block → Block 1 → Block 2 → Block 3 → ...
     ↓            ↓          ↓          ↓
  hash_0       hash_1     hash_2     hash_3
```

**Integrity formula:**
```
integrity_hash = SHA256(tensor_semantic || runtime_config || capsule_bindings)
prev_block_hash = integrity_hash of previous block
```

---

## Integration with SSOT

### Emit Runtime Block as Capsule

```python
from ssot_bridge import SSOTBridge

ssot = SSOTBridge()

# Generate runtime block
block = generator.generate_from_ipfs(ipfs_config)

# Emit to SSOT API
ssot.emit_capsule(
    payload={
        "schema": "tensor.runtime.v1",
        "runtime_block": block
    },
    governance_metadata={
        "maker_signature": "...",
        "checker_signature": "..."
    }
)
```

### Bind to Existing Capsules

```python
# Retrieve company registration capsule
company_capsule = game.get_company(company_id).registration_info()

# Compute binding hash
binding_hash = hashlib.sha256(
    json.dumps(company_capsule, sort_keys=True).encode()
).hexdigest()

# Generate runtime block with binding
block = generator.generate_from_local(
    config=my_runtime_config,
    capsule_bindings=[
        {
            "capsule_id": company_capsule["company_id"],
            "capsule_type": "company_registration",
            "binding_hash": binding_hash
        }
    ]
)
```

---

## Storage Location

### Option 1: Standalone Registry

Create `runtime/registry/tensor_runtime_blocks.json`:

```json
{
  "meta": {
    "schema": "tensor.runtime.registry.v1",
    "last_updated": "ISO8601"
  },
  "blocks": [
    { "block_id": "...", "integrity_hash": "...", ... },
    { "block_id": "...", "integrity_hash": "...", ... }
  ],
  "chain_valid": true
}
```

### Option 2: Embedded in SSOT Capsules

Each game state capsule can include `runtime_block_ref`:

```json
{
  "capsule_id": "...",
  "payload": {
    "game_state": { ... },
    "runtime_block_ref": {
      "block_id": "...",
      "integrity_hash": "...",
      "embedding_space": "cici.v1"
    }
  }
}
```

### Option 3: Database Table

```sql
CREATE TABLE runtime_blocks (
    block_id UUID PRIMARY KEY,
    schema_version TEXT,
    timestamp TIMESTAMPTZ,
    tensor_embedding VECTOR(16),  -- pgvector extension
    config_source TEXT,
    normalized_params JSONB,
    integrity_hash TEXT,
    prev_block_hash TEXT
);

CREATE INDEX idx_tensor_embedding ON runtime_blocks
USING ivfflat (tensor_embedding vector_cosine_ops);  -- For similarity search
```

---

## Example: IPFS → Runtime Block

### Input IPFS Config

```json
{
  "Addresses": {
    "API": "/ip4/127.0.0.1/tcp/5001",
    "Gateway": "/ip4/127.0.0.1/tcp/8080"
  },
  "Datastore": {
    "Type": "levelds",
    "Path": "~/.ipfs/datastore"
  }
}
```

### Generated Runtime Block

```json
{
  "block_id": "f7b3c8d2-4a1e-4c9b-8f3d-2e1a6b9c5d4f",
  "schema_version": "tensor.runtime.v1",
  "timestamp": "2026-01-11T04:15:00Z",
  
  "tensor_semantic": {
    "embedding_space": "cici.v1",
    "coordinates": [0.234, -0.567, 0.891, ...],  // 16D
    "manifold_type": "EUCLIDEAN",
    "dimension": 16
  },
  
  "runtime_config": {
    "config_source": "IPFS",
    "ipfs_cid": "QmExampleCID123",
    "normalized_params": {
      "network": {
        "api": "/ip4/127.0.0.1/tcp/5001",
        "gateway": "/ip4/127.0.0.1/tcp/8080"
      },
      "storage": {
        "type": "levelds",
        "path": "~/.ipfs/datastore"
      }
    },
    "raw_config": { /* original IPFS JSON */ }
  },
  
  "capsule_bindings": [],
  "integrity_hash": "a1b2c3d4e5f6...",
  "prev_block_hash": null,  // Genesis
  
  "metadata": {
    "creator": "enterprise_business_game",
    "purpose": "IPFS node runtime",
    "tags": ["ipfs", "p2p"]
  }
}
```

---

## Verification

### Run Generator Demo

```bash
cd C:\Users\eqhsp\.gemini\antigravity\scratch\enterprise_business_game\src
python runtime_block_generator.py
```

**Output:**
- Generated runtime block (JSON)
- Integrity verification: ✓ PASS

### Validate Against Schema

```bash
pip install jsonschema
python -c "
import json
import jsonschema

with open('../schemas/unified_tensor_runtime_block.v1.schema.json') as f:
    schema = json.load(f)

with open('example_block.json') as f:
    block = json.load(f)

jsonschema.validate(instance=block, schema=schema)
print('✓ Schema validation passed')
"
```

---

## Next Steps

1. **Define your IPFS JSON structure** — Provide the exact JSON so I can customize normalization
2. **Choose storage location** — Registry file, SSOT capsules, or database?
3. **Integrate with Master Agent** — Use runtime blocks to configure self-tuning behavior

Would you like me to:
- Customize the IPFS normalization for your specific use case?
- Create a registry file generator?
- Build a Flask/FastAPI endpoint for runtime block CRUD operations?
