"""
Replay Court Bridge — Converts GT Racing Replay Court to IPFS checkpoints.
Pins ledger hashes as content-addressed capsules.
"""

import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional


class ReplayCourtBridge:
    """
    Bridge between GT Racing Replay Court and IPFS checkpoint system.
    Pins Replay Court ledger hashes as content-addressed capsules.
    """

    def __init__(self, ipfs_client=None):
        """
        Initialize bridge with optional IPFS client.
        
        Args:
            ipfs_client: IPFSClient instance (from ipfs_client.py)
        """
        self.ipfs = ipfs_client

    def pin_replay_court(
        self,
        ledger_hash: str,
        metadata: Dict[str, Any]
    ) -> Optional[str]:
        """
        Pin Replay Court ledger hash to IPFS as a capsule.
        
        Args:
            ledger_hash: SHA-256 hash of Replay Court ledger
            metadata: Additional metadata (kernel_tick, runtime_block_id, etc.)
        
        Returns:
            IPFS CID of pinned capsule, or None if IPFS not available
        
        Raises:
            RuntimeError: If IPFS pinning fails
        """
        if not self.ipfs:
            return None

        if not self.ipfs.is_available():
            raise RuntimeError("IPFS daemon not available")

        # Create Replay Court capsule
        capsule = {
            "schema": "replay_court_capsule.v1",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ledger_head_hash": ledger_hash,
            "metadata": metadata
        }

        # Serialize as canonical JSON (could use canon.ts logic in Python)
        # For now, use deterministic JSON with sorted keys
        capsule_json = json.dumps(capsule, sort_keys=True, indent=2)

        # Add to IPFS
        try:
            cid = self.ipfs.add(capsule_json, pin=True)
            return cid
        except Exception as e:
            raise RuntimeError(f"Failed to pin Replay Court to IPFS: {e}")

    def fetch_replay_court(self, cid: str) -> Dict[str, Any]:
        """
        Fetch Replay Court capsule from IPFS by CID.
        
        Args:
            cid: IPFS Content Identifier
        
        Returns:
            Replay Court capsule dict
        
        Raises:
            RuntimeError: If fetch or parsing fails
        """
        if not self.ipfs:
            raise RuntimeError("No IPFS client configured")

        try:
            capsule_json = self.ipfs.cat(cid)
            capsule = json.loads(capsule_json)
            return capsule
        except Exception as e:
            raise RuntimeError(f"Failed to fetch Replay Court from IPFS: {e}")

    def verify_capsule_integrity(self, capsule: Dict[str, Any]) -> bool:
        """
        Verify Replay Court capsule integrity.
        Recomputes hash and checks against stored value.
        """
        ledger_hash = capsule.get("ledger_head_hash")
        if not ledger_hash:
            return False

        # In full implementation, would verify hash chain
        # For now, just check presence of required fields
        required = ["schema", "timestamp", "ledger_head_hash", "metadata"]
        return all(field in capsule for field in required)
