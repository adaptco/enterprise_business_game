"""
Kernel Boot System — Main orchestrator for runtime block execution.
Implements deterministic state machine with IPFS checkpointing.
"""

import json
import hashlib
import sys
import os
from typing import Dict, Any, Optional
from enum import Enum

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.runtime_block_generator import RuntimeBlockGenerator, ManifoldType
from ipfs_client import IPFSClient  
from checkpoint_manager import CheckpointManager
from agent_pool import ExpertAgentPool
try:
    from src.ssot_bridge import SSOTBridge
except ImportError:
    SSOTBridge = None  # Optional dependency


class KernelPhase(Enum):
    """Kernel execution phases"""
    BOOT = "BOOT"
    EXEC = "EXEC"
    VERIFY = "VERIFY"
    CHECKPOINT = "CHECKPOINT"
    HALT = "HALT"


class KernelState:
    """Deterministic kernel state"""
    
    def __init__(self):
        self.phase = KernelPhase.BOOT
        self.tick = 0
        self.runtime_block: Optional[Dict[str, Any]] = None
        self.checkpoint_cid: Optional[str] = None
        self.agent_outputs: list = []

    def compute_state_hash(self) -> str:
        """Compute SHA-256 of current state"""
        state_data = {
            "phase": self.phase.value,
            "tick": self.tick,
            "runtime_block_hash": self.runtime_block["integrity_hash"] if self.runtime_block else None,
            "checkpoint_cid": self.checkpoint_cid
        }
        canonical = json.dumps(state_data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()


class KernelBootSystem:
    """
    Main kernel boot orchestrator.
    Loads runtime blocks, executes expert agents, and emits checkpoints to IPFS.
    """

    def __init__(self, config_path: str = "config/runtime_genesis.json"):
        self.state = KernelState()
        self.ipfs = IPFSClient()
        self.checkpoint_mgr = CheckpointManager()
        self.ssot = SSOTBridge() if SSOTBridge else None
        self.agent_pool = ExpertAgentPool()
        
        # Load configuration
        if os.path.exists(config_path):
            with open(config_path) as f:
                self.config = json.load(f)
        else:
            # Default config if file doesn't exist
            self.config = {
                "checkpoint_interval": 10,
                "ssot_enabled": False,
                "runtime_params": {}
            }

    def boot(self) -> bool:
        """Phase 1: BOOT — Load runtime block and initialize"""
        print("\n" + "="*60)
        print("🚀 KERNEL BOOT: Phase BOOT")
        print("="*60)
        
        # Check if IPFS is available
        ipfs_available = self.ipfs.is_available()
        if not ipfs_available:
            print("⚠️  IPFS daemon not running - IPFS features disabled")
        else:
            peer_id = self.ipfs.get_peer_id()
            print(f"✓ IPFS connected: {peer_id[:16] if peer_id else 'unknown'}...")
        
        # Load runtime block from IPFS or local
        if ipfs_available and "ipfs_cid" in self.config:
            print(f"\n📥 Fetching runtime block from IPFS: {self.config['ipfs_cid']}")
            try:
                runtime_json = self.ipfs.cat(self.config['ipfs_cid'])
                self.state.runtime_block = json.loads(runtime_json)
                print("✓ Runtime block fetched from IPFS")
            except Exception as e:
                print(f"❌ IPFS fetch failed: {e}")
                print("   Falling back to local genesis...")
                self.state.runtime_block = None
        
        if not self.state.runtime_block:
            print("\n📁 Loading runtime block from local genesis")
            generator = RuntimeBlockGenerator(embedding_space="kernel.v1")
            self.state.runtime_block = generator.generate_from_local(
                config=self.config.get("runtime_params", {
                    "kernel": {"version": "1.0.0"},
                    "execution": {"deterministic": True}
                }),
                manifold_type=ManifoldType.EUCLIDEAN,
                metadata={
                    "creator": "kernel_boot_system",
                    "purpose": "Runtime orchestration",
                    "tags": ["kernel", "boot", "deterministic"]
                }
            )

        # Verify integrity
        generator = RuntimeBlockGenerator()
        if not generator.verify_block_integrity(self.state.runtime_block):
            print("\n❌ BOOT FAILED: Runtime block integrity check failed")
            self.state.phase = KernelPhase.HALT
            return False

        print(f"\n✓ Runtime block loaded: {self.state.runtime_block['block_id'][:8]}...")
        print(f"  Embedding space: {self.state.runtime_block['tensor_semantic']['embedding_space']}")
        print(f"  Dimension: {self.state.runtime_block['tensor_semantic']['dimension']}")
        print(f"  Manifold: {self.state.runtime_block['tensor_semantic']['manifold_type']}")
        
        # Initialize expert agents
        print("\n🤖 Initializing expert agent pool...")
        self.agent_pool.initialize(self.state.runtime_block)
        
        # Transition to EXEC
        self.state.phase = KernelPhase.EXEC
        print("\n✓ BOOT complete. Transitioning to EXEC phase.")
        print("="*60 + "\n")
        return True

    def execute_tick(self):
        """Phase 2: EXEC — Execute one tick of agent processing"""
        if self.state.phase != KernelPhase.EXEC:
            return

        print(f"⏱️  EXEC Tick {self.state.tick}")
        
        # Run all expert agents
        tick_outputs = self.agent_pool.execute_tick(
            tick=self.state.tick,
            runtime_block=self.state.runtime_block
        )
        
        self.state.agent_outputs.extend(tick_outputs)
        self.state.tick += 1
        
        # Checkpoint every N ticks
        checkpoint_interval = self.config.get("checkpoint_interval", 10)
        if self.state.tick % checkpoint_interval == 0:
            self.state.phase = KernelPhase.CHECKPOINT

    def checkpoint(self):
        """Phase 3: CHECKPOINT — Emit state to IPFS and SSOT"""
        print(f"\n" + "="*60)
        print(f"💾 CHECKPOINT: Tick {self.state.tick}")
        print("="*60)
        
        # Create checkpoint capsule
        checkpoint = self.checkpoint_mgr.create_capsule(
            tick=self.state.tick,
            kernel_state=self.state.compute_state_hash(),
            runtime_block=self.state.runtime_block,
            agent_outputs=self.state.agent_outputs[-10:]  # Last 10 outputs
        )
        
        print(f"✓ Checkpoint capsule created: {checkpoint['capsule_id'][:8]}...")
        
        # Pin to IPFS (if available)
        if self.ipfs.is_available():
            try:
                checkpoint_json = json.dumps(checkpoint, indent=2)
                cid = self.ipfs.add(checkpoint_json, pin=True)
                self.state.checkpoint_cid = cid
                print(f"✓ Checkpoint pinned to IPFS: {cid}")
            except Exception as e:
                print(f"⚠️  IPFS pinning failed: {e}")
                print("   Checkpoint saved locally only")
        else:
            print("⚠️  IPFS not available - checkpoint saved locally only")
        
        # Emit to SSOT (if enabled)
        if self.config.get("ssot_enabled", False) and self.ssot:
            try:
                self.ssot.emit_capsule(checkpoint)
                print("✓ Emitted to SSOT")
            except Exception as e:
                print(f"⚠️  SSOT emission failed: {e}")
        
        print("="*60 + "\n")
        
        # Return to EXEC
        self.state.phase = KernelPhase.EXEC

    def run(self, max_ticks: int = 100):
        """Main execution loop"""
        if not self.boot():
            print("\n❌ Kernel boot failed - halting")
            return
        
        while self.state.tick < max_ticks and self.state.phase != KernelPhase.HALT:
            if self.state.phase == KernelPhase.EXEC:
                self.execute_tick()
            elif self.state.phase == KernelPhase.CHECKPOINT:
                self.checkpoint()
        
        # Final summary
        print("\n" + "="*60)
        print("🏁 Kernel execution complete")
        print("="*60)
        print(f"  Total ticks: {self.state.tick}")
        print(f"  Agent outputs: {len(self.state.agent_outputs)}")
        print(f"  Checkpoints: {len(self.checkpoint_mgr.checkpoints)}")
        print(f"  Final state hash: {self.state.compute_state_hash()[:16]}...")
        
        # Verify checkpoint chain  
        chain_valid = self.checkpoint_mgr.verify_chain()
        print(f"  Checkpoint chain: {'✓ INTACT' if chain_valid else '✗ CORRUPTED'}")
        
        # Agent summaries
        print("\n🤖 Agent Performance:")
        for agent_name, summary in self.agent_pool.get_agent_summaries().items():
            print(f"  {agent_name}: {summary['total_outputs']} outputs")
        
        print("="*60 + "\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Kernel Boot System")
    parser.add_argument("--boot", action="store_true", help="Run boot sequence")
    parser.add_argument("--config", default="config/runtime_genesis.json", help="Config file path")
    parser.add_argument("--ticks", type=int, default=50, help="Maximum ticks to run")
    
    args = parser.parse_args()
    
    kernel = KernelBootSystem(config_path=args.config)
    kernel.run(max_ticks=args.ticks)
