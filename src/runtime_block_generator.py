"""
Unified Tensor Runtime Block Generator
Derives encapsulated runtime blocks from external configurations (IPFS, local files, etc.)
with semantic tensor embeddings and Merkle chain integrity.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from enum import Enum


class ConfigSource(Enum):
    """Configuration data source types"""
    IPFS = "IPFS"
    LOCAL = "LOCAL"
    REGISTRY = "REGISTRY"
    EXTERNAL = "EXTERNAL"


class ManifoldType(Enum):
    """Geometric manifold types for tensor embedding"""
    EUCLIDEAN = "EUCLIDEAN"
    SE3 = "SE3"
    PINN = "PINN"
    CUSTOM = "CUSTOM"


class RuntimeBlockGenerator:
    """
    Generates unified tensor runtime blocks from external configurations.
    Implements deterministic tensor embedding and hash-chained lineage.
    """

    def __init__(self, embedding_space: str = "default.v1"):
        self.embedding_space = embedding_space
        self.prev_block_hash: Optional[str] = None

    def compute_integrity_hash(self, block_data: Dict[str, Any]) -> str:
        """Compute SHA-256 hash of runtime block (deterministic)"""
        # Extract hashable fields
        hashable = {
            "tensor_semantic": block_data["tensor_semantic"],
            "runtime_config": {
                "config_source": block_data["runtime_config"]["config_source"],
                "normalized_params": block_data["runtime_config"]["normalized_params"]
            },
            "capsule_bindings": block_data.get("capsule_bindings", [])
        }
        
        # Deterministic canonical JSON
        canonical_json = json.dumps(hashable, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

    def embed_tensor_from_config(
        self,
        config: Dict[str, Any],
        manifold_type: ManifoldType = ManifoldType.EUCLIDEAN
    ) -> Dict[str, Any]:
        """
        Derive semantic tensor coordinates from configuration.
        This is a simplified embedding — real implementation would use ML/geometric methods.
        """
        # Extract numeric features from config for embedding
        features = self._extract_features(config)
        
        # Simple hash-based embedding (deterministic)
        # In production, use learned embeddings or geometric projections
        config_str = json.dumps(config, sort_keys=True)
        hash_bytes = hashlib.sha256(config_str.encode()).digest()
        
        # Convert hash to normalized coordinates
        dimension = len(features) if features else 16
        coordinates = [
            (int.from_bytes(hash_bytes[i:i+2], 'big') / 65535.0) * 2 - 1
            for i in range(0, min(dimension * 2, len(hash_bytes)), 2)
        ]
        
        return {
            "embedding_space": self.embedding_space,
            "coordinates": coordinates,
            "manifold_type": manifold_type.value,
            "dimension": len(coordinates)
        }

    def _extract_features(self, config: Dict[str, Any]) -> List[float]:
        """Extract numeric features from config for tensor embedding"""
        features = []
        
        def traverse(obj: Any):
            if isinstance(obj, (int, float)):
                features.append(float(obj))
            elif isinstance(obj, dict):
                for v in obj.values():
                    traverse(v)
            elif isinstance(obj, list):
                for item in obj:
                    traverse(item)
        
        traverse(config)
        return features

    def normalize_ipfs_config(self, ipfs_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize IPFS-style configuration into standard runtime params.
        Override this method for custom normalization rules.
        """
        # Default normalization: flatten nested structures, extract key params
        normalized = {}
        
        # Example transformations (customize based on your IPFS schema):
        if "Addresses" in ipfs_json:
            normalized["network"] = {
                "api": ipfs_json["Addresses"].get("API"),
                "gateway": ipfs_json["Addresses"].get("Gateway"),
                "swarm": ipfs_json["Addresses"].get("Swarm", [])
            }
        
        if "Datastore" in ipfs_json:
            normalized["storage"] = {
                "type": ipfs_json["Datastore"].get("Type"),
                "path": ipfs_json["Datastore"].get("Path"),
                "spec": ipfs_json["Datastore"].get("Spec")
            }
        
        if "Bootstrap" in ipfs_json:
            normalized["bootstrap_peers"] = ipfs_json["Bootstrap"]
        
        # Pass through other top-level keys
        for key in ["Identity", "Discovery", "Routing", "Swarm", "Pubsub"]:
            if key in ipfs_json:
                normalized[key.lower()] = ipfs_json[key]
        
        return normalized

    def generate_from_ipfs(
        self,
        ipfs_json: Dict[str, Any],
        ipfs_cid: Optional[str] = None,
        capsule_bindings: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate unified tensor runtime block from IPFS configuration.
        
        Args:
            ipfs_json: IPFS configuration JSON
            ipfs_cid: Content Identifier (optional)
            capsule_bindings: List of bound capsules with hashes
            metadata: Optional metadata for the block
        
        Returns:
            Complete runtime block conforming to unified_tensor_runtime_block.v1.schema.json
        """
        # Normalize IPFS config
        normalized_params = self.normalize_ipfs_config(ipfs_json)
        
        # Generate tensor embedding
        tensor_semantic = self.embed_tensor_from_config(
            normalized_params,
            manifold_type=ManifoldType.EUCLIDEAN
        )
        
        # Build runtime block
        block = {
            "block_id": str(uuid.uuid4()),
            "schema_version": "tensor.runtime.v1",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tensor_semantic": tensor_semantic,
            "runtime_config": {
                "config_source": ConfigSource.IPFS.value,
                "normalized_params": normalized_params,
                "raw_config": ipfs_json  # Keep original for audit
            },
            "prev_block_hash": self.prev_block_hash
        }
        
        if ipfs_cid:
            block["runtime_config"]["ipfs_cid"] = ipfs_cid
        
        if capsule_bindings:
            block["capsule_bindings"] = capsule_bindings
        
        if metadata:
            block["metadata"] = metadata
        
        # Compute integrity hash
        block["integrity_hash"] = self.compute_integrity_hash(block)
        
        # Update chain
        self.prev_block_hash = block["integrity_hash"]
        
        return block

    def generate_from_local(
        self,
        config: Dict[str, Any],
        manifold_type: ManifoldType = ManifoldType.EUCLIDEAN,
        capsule_bindings: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate unified tensor runtime block from local configuration.
        """
        # Generate tensor embedding
        tensor_semantic = self.embed_tensor_from_config(config, manifold_type)
        
        # Build runtime block
        block = {
            "block_id": str(uuid.uuid4()),
            "schema_version": "tensor.runtime.v1",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tensor_semantic": tensor_semantic,
            "runtime_config": {
                "config_source": ConfigSource.LOCAL.value,
                "normalized_params": config
            },
            "prev_block_hash": self.prev_block_hash
        }
        
        if capsule_bindings:
            block["capsule_bindings"] = capsule_bindings
        
        if metadata:
            block["metadata"] = metadata
        
        # Compute integrity hash
        block["integrity_hash"] = self.compute_integrity_hash(block)
        
        # Update chain
        self.prev_block_hash = block["integrity_hash"]
        
        return block

    def verify_block_integrity(self, block: Dict[str, Any]) -> bool:
        """Verify integrity hash of a runtime block"""
        claimed_hash = block.get("integrity_hash")
        computed_hash = self.compute_integrity_hash(block)
        return claimed_hash == computed_hash

    def verify_chain(self, blocks: List[Dict[str, Any]]) -> bool:
        """Verify Merkle chain of runtime blocks"""
        for i in range(1, len(blocks)):
            current = blocks[i]
            previous = blocks[i - 1]
            
            # Verify integrity
            if not self.verify_block_integrity(current):
                return False
            
            # Verify link
            expected_prev = previous["integrity_hash"]
            actual_prev = current["prev_block_hash"]
            
            if expected_prev != actual_prev:
                return False
        
        return True


# Example usage
if __name__ == "__main__":
    generator = RuntimeBlockGenerator(embedding_space="cici.v1")
    
    # Example IPFS-style config
    example_ipfs_config = {
        "Addresses": {
            "API": "/ip4/127.0.0.1/tcp/5001",
            "Gateway": "/ip4/127.0.0.1/tcp/8080",
            "Swarm": [
                "/ip4/0.0.0.0/tcp/4001",
                "/ip6/::/tcp/4001"
            ]
        },
        "Datastore": {
            "Type": "levelds",
            "Path": "~/.ipfs/datastore",
            "Spec": {
                "type": "mount",
                "mounts": [
                    {"mountpoint": "/blocks", "type": "flatfs"},
                    {"mountpoint": "/", "type": "levelds"}
                ]
            }
        },
        "Bootstrap": [
            "/dnsaddr/bootstrap.libp2p.io/p2p/QmNnooDu7bfjPFoTZYxMNLWUQJyrVwtbZg5gBMjTezGAJN"
        ],
        "Identity": {
            "PeerID": "QmExamplePeerID123456789"
        }
    }
    
    # Generate runtime block
    block = generator.generate_from_ipfs(
        ipfs_json=example_ipfs_config,
        ipfs_cid="QmExampleCID",
        metadata={
            "creator": "enterprise_business_game",
            "purpose": "IPFS node runtime configuration",
            "tags": ["ipfs", "p2p", "distributed"]
        }
    )
    
    # Print result
    print(json.dumps(block, indent=2))
    
    # Verify integrity
    print(f"\n✓ Block integrity: {generator.verify_block_integrity(block)}")
