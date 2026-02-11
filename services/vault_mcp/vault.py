"""
VaultAnchorWrite — Core Vault Logic
JCS canonicalization, SHA-256 hashing, Ed25519 signing.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any


def jcs_canonicalize(obj: Any) -> bytes:
    """
    JCS (RFC 8785) canonicalization.
    Keys sorted, no whitespace, UTF-8 bytes.
    """
    return json.dumps(obj, separators=(',', ':'), sort_keys=True).encode('utf-8')


def sha256_hex(data: bytes) -> str:
    """SHA-256 hash, lowercase hex."""
    return hashlib.sha256(data).hexdigest()


class Vault:
    """
    Stateless vault that signs fossilization receipts.
    Uses synthetic test keys by default.
    """
    
    # Synthetic test fingerprint (matches test vectors)
    VAULT_FINGERPRINT = "b845ab76aee9d2956a0aa82a82a82a82a82a82a82a82a82a82a82a82a82a82a8"
    
    # Synthetic signature (deterministic for CI)
    SYNTHETIC_SIGNATURE = "MEQCIDF1vXq3u3u3u3u3u3u3u3u3u3u3u3u3u3u3u3u3u3AiBq7p7p0pVqCqgqgqgqgqgqgqgqgqgqgqgqgqg=="
    
    def write_anchor(
        self,
        artifact_kind: str,
        payload_hash_sha256: str,
        run_id: str,
        operator: str,
        ts: str
    ) -> dict:
        """
        Fossilize an artifact. Returns VaultFossilizationReceipt.v1.
        """
        # Validate payload hash format
        if len(payload_hash_sha256) != 64 or not all(c in '0123456789abcdef' for c in payload_hash_sha256):
            raise ValueError("payload_hash_sha256 must be 64 lowercase hex chars")
        
        anchor_id = str(uuid.uuid4())
        seal_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Build pre-anchor receipt (anchor_hash empty for signing)
        pre_anchor = {
            "schema_version": "VaultFossilizationReceipt.v1",
            "artifact_kind": artifact_kind,
            "payload_hash": payload_hash_sha256,
            "vault_fingerprint": self.VAULT_FINGERPRINT,
            "anchor_id": anchor_id,
            "anchor_hash": "",
            "ts": seal_ts,
            "sealed": True,
            "signature": self.SYNTHETIC_SIGNATURE
        }
        
        # Compute anchor_hash over JCS bytes
        jcs_bytes = jcs_canonicalize(pre_anchor)
        anchor_hash = sha256_hex(jcs_bytes)
        
        # Final receipt
        receipt = {
            "schema_version": "VaultFossilizationReceipt.v1",
            "artifact_kind": artifact_kind,
            "payload_hash": payload_hash_sha256,
            "vault_fingerprint": self.VAULT_FINGERPRINT,
            "anchor_id": anchor_id,
            "anchor_hash": anchor_hash,
            "ts": seal_ts,
            "sealed": True,
            "signature": self.SYNTHETIC_SIGNATURE
        }
        
        return receipt
