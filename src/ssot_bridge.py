"""
SSOT Bridge - integrates game simulation with existing SSOT infrastructure.
Emits sovereign state capsules to SSOT API for audit trail persistence.
"""

import hashlib
import json
import uuid
import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional


class SSOTBridge:
    """
    Client for SSOT API integration.
    Implements determinism contract v1 for capsule emission.
    """

    def __init__(self, ssot_api_url: str = "http://localhost:8000"):
        self.ssot_api_url = ssot_api_url
        self.last_capsule_hash: Optional[str] = None

    def get_latest_hash(self) -> Optional[str]:
        """Fetch latest capsule hash from SSOT API"""
        try:
            response = requests.get(f"{self.ssot_api_url}/lineage/latest")
            response.raise_for_status()
            data = response.json()
            return data.get("latest_hash")
        except Exception as e:
            print(f"⚠️  Failed to fetch latest hash from SSOT: {e}")
            return None

    def compute_payload_hash(self, payload: Dict[str, Any]) -> str:
        """Compute SHA-256 hash of payload (deterministic)"""
        canonical_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

    def emit_capsule(
        self,
        payload: Dict[str, Any],
        governance_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Emit a sovereign state capsule to SSOT API.
        Returns the capsule hash if successful, None if failed.
        """
        # Get latest hash for Merkle linking
        fossilized_link = self.last_capsule_hash or self.get_latest_hash()

        # Create capsule
        capsule = {
            "capsule_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "state_integrity": self.compute_payload_hash(payload),
            "fossilized_link": fossilized_link,
            "payload": payload
        }

        if governance_metadata:
            capsule["governance_metadata"] = governance_metadata

        # Send to SSOT API
        try:
            response = requests.post(
                f"{self.ssot_api_url}/ingest",
                json=capsule
            )
            response.raise_for_status()

            # Compute capsule hash for next link
            capsule_hash = self.compute_payload_hash(capsule)
            self.last_capsule_hash = capsule_hash

            print(f"✓ Emitted SSOT capsule: {capsule['capsule_id'][:8]}... (hash: {capsule_hash[:16]}...)")
            return capsule_hash

        except Exception as e:
            print(f"⚠️  Failed to emit capsule to SSOT: {e}")
            return None

    def emit_game_state_capsule(
        self,
        tick: int,
        market_state: Dict[str, Any],
        company_snapshots: list[Dict[str, Any]]
    ) -> Optional[str]:
        """Convenience method to emit game state as SSOT capsule"""
        payload = {
            "schema": "game_state.v1",
            "tick": tick,
            "market_state": market_state,
            "company_snapshots": company_snapshots
        }

        return self.emit_capsule(payload)

    def verify_lineage(self) -> bool:
        """Verify that local hash matches SSOT API latest hash"""
        remote_hash = self.get_latest_hash()
        if remote_hash and self.last_capsule_hash:
            return remote_hash == self.last_capsule_hash
        return True  # No mismatch if no comparison possible

    def export_audit_manifest(self, game_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate full audit manifest combining game ledger + SSOT capsules.
        This is the "tamper-evident export" for replay verification.
        """
        return {
            "meta": {
                "schema": "audit_manifest.v1",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "ssot_api_url": self.ssot_api_url
            },
            "game_data": game_data,
            "ssot_lineage": {
                "last_capsule_hash": self.last_capsule_hash,
                "remote_latest_hash": self.get_latest_hash()
            }
        }
