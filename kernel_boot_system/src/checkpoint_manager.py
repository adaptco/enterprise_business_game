"""
Checkpoint Manager — Creates and manages checkpoint capsules.
Emits deterministic snapshots of kernel state.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


class CheckpointManager:
    """
    Manages checkpoint capsule creation and verification.
    Implements deterministic snapshot protocol.
    """

    def __init__(self):
        self.checkpoints: List[Dict[str, Any]] = []
        self.prev_checkpoint_hash: Optional[str] = None

    def create_capsule(
        self,
        tick: int,
        kernel_state: str,
        runtime_block: Dict[str, Any],
        agent_outputs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create checkpoint capsule at current tick.
        
        Args:
            tick: Current tick number
            kernel_state: SHA-256 hash of kernel state
            runtime_block: Runtime block being executed
            agent_outputs: Recent agent outputs
        
        Returns:
            Checkpoint capsule conforming to checkpoint_capsule.v1.schema.json
        """
        capsule = {
            "capsule_id": str(uuid.uuid4()),
            "schema": "checkpoint_capsule.v1",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tick": tick,
            "kernel_state_hash": kernel_state,
            "runtime_block_ref": {
                "block_id": runtime_block["block_id"],
                "integrity_hash": runtime_block["integrity_hash"],
                "embedding_space": runtime_block["tensor_semantic"]["embedding_space"]
            },
            "agent_outputs": agent_outputs,
            "prev_checkpoint_hash": self.prev_checkpoint_hash
        }

        # Compute checkpoint integrity hash
        capsule["checkpoint_hash"] = self._compute_hash(capsule)

        # Update chain
        self.prev_checkpoint_hash = capsule["checkpoint_hash"]
        self.checkpoints.append(capsule)

        return capsule

    def _compute_hash(self, capsule: Dict[str, Any]) -> str:
        """Compute SHA-256 of checkpoint capsule"""
        # Exclude the hash field itself
        hashable = {k: v for k, v in capsule.items() if k != "checkpoint_hash"}
        canonical = json.dumps(hashable, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()

    def verify_checkpoint(self, capsule: Dict[str, Any]) -> bool:
        """Verify checkpoint integrity"""
        claimed_hash = capsule.get("checkpoint_hash")
        computed_hash = self._compute_hash(capsule)
        return claimed_hash == computed_hash

    def verify_chain(self) -> bool:
        """Verify entire checkpoint chain"""
        for i in range(1, len(self.checkpoints)):
            current = self.checkpoints[i]
            previous = self.checkpoints[i - 1]

            # Verify integrity
            if not self.verify_checkpoint(current):
                return False

            # Verify link
            if current["prev_checkpoint_hash"] != previous["checkpoint_hash"]:
                return False

        return True

    def get_latest_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Get most recent checkpoint"""
        return self.checkpoints[-1] if self.checkpoints else None

    def export_chain(self) -> List[Dict[str, Any]]:
        """Export complete checkpoint chain"""
        return self.checkpoints.copy()
