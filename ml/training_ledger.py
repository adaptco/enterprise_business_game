"""
Training Checkpoint Ledger for Hamiltonian LoRA
Merkle-chained training history with canonical hashing.
"""

import hashlib
import json
import numpy as np
import torch
from dataclasses import dataclass, asdict
from typing import Optional, List
from datetime import datetime, timezone
import logging
import sys
import os

# Add brain to path for TokenBillingAgent
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../brain")))

try:
    from token_billing_agent.token_billing_agent import TokenBillingAgent
except ImportError:
    logging.warning("TokenBillingAgent not found in path. Billing features disabled.")
    TokenBillingAgent = None

logger = logging.getLogger("TrainingLedger")


@dataclass
class TrainingCheckpoint:
    """
    Training checkpoint with Merkle chain linkage.
    All numeric values stored as integers for canonical hashing.
    """
    step: int
    timestamp: str
    loss_scaled: int  # loss * 10000 (4 decimal precision)
    
    # Eigenspace snapshot (integers)
    eigenvalues_scaled: List[int]  # λ * 100
    eigenvalue_sum_scaled: int
    effective_rank: int
    
    # LoRA state hashes
    lora_A_hash: str  # SHA-256 of quantized A
    lora_B_hash: str  # SHA-256 of quantized B
    
    # Merkle chain
    prev_checkpoint_hash: Optional[str]
    checkpoint_hash: str
    
    # Metadata
    rank: int
    alpha_scaled: int  # alpha * 100
    
    # Billing / Agent Identity
    agent_signature: Optional[str] = None
    orientation_id: Optional[str] = None  # The "Origin Point" ID
    

def fp16_to_canonical_int16(tensor: torch.Tensor, scale: int = 1000) -> np.ndarray:
    """
    Convert FP16 tensor to canonical int16 representation.
    
    Args:
        tensor: FP16 tensor
        scale: Scaling factor (default 1000)
    
    Returns:
        int16 numpy array (deterministic, hashable)
    """
    arr = tensor.detach().cpu().numpy()
    arr_scaled = (arr * scale).round()
    
    # Clamp to int16 range
    arr_int16 = np.clip(arr_scaled, -32768, 32767).astype(np.int16)
    
    return arr_int16


def hash_fp16_tensor(tensor: torch.Tensor, scale: int = 1000) -> str:
    """
    Compute deterministic SHA-256 hash of FP16 tensor.
    
    Args:
        tensor: FP16 tensor (any shape)
        scale: Scaling factor for quantization
    
    Returns:
        Hex digest of SHA-256 hash
    """
    arr_int16 = fp16_to_canonical_int16(tensor, scale)
    digest = hashlib.sha256(arr_int16.tobytes()).hexdigest()
    return digest





def create_training_checkpoint(
    step: int,
    loss: float,
    eigenvalues: torch.Tensor,
    lora_A: torch.Tensor,
    lora_B: torch.Tensor,
    prev_hash: Optional[str],
    rank: int,
    alpha: float,
    agent: Optional[TokenBillingAgent] = None,
    customer_id: str = "default_user",
    orientation_id: str = "origin_0"
) -> TrainingCheckpoint:
    """
    Create training checkpoint with canonical hashing and billing attribution.
    """
    # 1. Prepare data (reuse logic by refactoring or duplicating slightly for safety)
    loss_int = int(loss * 10000)
    alpha_int = int(alpha * 100)
    eigenvalues_scaled = [int(ev.item() * 100) for ev in eigenvalues]
    eigenvalue_sum = int(eigenvalues.sum().item() * 100)
    threshold = eigenvalues[0].item() * 0.01
    effective_rank = int((eigenvalues > threshold).sum().item())
    
    lora_A_hash = hash_fp16_tensor(lora_A, scale=1000)
    lora_B_hash = hash_fp16_tensor(lora_B, scale=1000)
    
    checkpoint_obj = {
        "step": step,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "loss_scaled": loss_int,
        "eigenvalues_scaled": eigenvalues_scaled,
        "eigenvalue_sum_scaled": eigenvalue_sum,
        "effective_rank": effective_rank,
        "lora_A_hash": lora_A_hash,
        "lora_B_hash": lora_B_hash,
        "rank": rank,
        "alpha_scaled": alpha_int,
        "prev_checkpoint_hash": prev_hash,
        "orientation_id": orientation_id
    }
    
    # Log usage to agent if present
    agent_signature = None
    if agent:
        # Log 1 token per step for simplicity, or based on compute
        # Using "TrainingFoundation" as model
        entry = agent.log_token_usage(
            customer_id=customer_id,
            tokens=100, # Flat rate per checkpoint
            model="foundation_training_v1",
            operation="checkpoint",
            metadata={"step": step, "rank": rank}
        )
        agent_signature = entry["hash"]
        checkpoint_obj["agent_signature"] = agent_signature

    canonical_json = json.dumps(checkpoint_obj, sort_keys=True, separators=(',', ':'))
    checkpoint_hash = hashlib.sha256(canonical_json.encode()).hexdigest()
    
    checkpoint = TrainingCheckpoint(
        step=step,
        timestamp=checkpoint_obj["timestamp"],
        loss_scaled=loss_int,
        eigenvalues_scaled=eigenvalues_scaled,
        eigenvalue_sum_scaled=eigenvalue_sum,
        effective_rank=effective_rank,
        lora_A_hash=lora_A_hash,
        lora_B_hash=lora_B_hash,
        prev_checkpoint_hash=prev_hash,
        checkpoint_hash=checkpoint_hash,
        rank=rank,
        alpha_scaled=alpha_int,
        agent_signature=agent_signature,
        orientation_id=orientation_id
    )
    
    logger.info(f"Checkpoint created: step={step}, hash={checkpoint_hash[:16]}... Agent={bool(agent)}")
    
    return checkpoint


def create_orientation_node(
    agent: TokenBillingAgent,
    customer_id: str,
    initial_config: dict
) -> TrainingCheckpoint:
    """
    Establish the Origin Point (Genesis Block) for the Foundation Model training.
    Embeds the agent context to orient the ledger.
    """
    logger.info(f"Creating Orientation Node for Customer: {customer_id}")
    
    # Generate random initialization for origin
    dummy_A = torch.zeros(512, 16, dtype=torch.float16)
    dummy_B = torch.zeros(16, 512, dtype=torch.float16)
    dummy_eig = torch.zeros(4, dtype=torch.float16)
    
    return create_training_checkpoint(
        step=0,
        loss=1.0,
        eigenvalues=dummy_eig,
        lora_A=dummy_A,
        lora_B=dummy_B,
        prev_hash=None,
        rank=16,
        alpha=16.0,
        agent=agent,
        customer_id=customer_id,
        orientation_id="ORIGIN_GENESIS_V1"
    )


def verify_checkpoint_chain(checkpoints: List[TrainingCheckpoint]) -> bool:
    """
    Verify Merkle chain integrity of training checkpoints.
    
    Args:
        checkpoints: List of checkpoints in order
    
    Returns:
        True if chain is intact, False otherwise
    """
    if not checkpoints:
        return True
    
    # First checkpoint should have None prev_hash
    if checkpoints[0].prev_checkpoint_hash is not None:
        logger.error("Genesis checkpoint has non-null prev_hash")
        return False
    
    # Verify each link
    for i in range(1, len(checkpoints)):
        curr = checkpoints[i]
        prev = checkpoints[i-1]
        
        if curr.prev_checkpoint_hash != prev.checkpoint_hash:
            logger.error(
                f"Chain break at step {curr.step}: "
                f"expected {prev.checkpoint_hash}, got {curr.prev_checkpoint_hash}"
            )
            return False
    
    logger.info(f"[OK] Verified {len(checkpoints)} checkpoints in chain")
    return True


def export_ledger_ndjson(checkpoints: List[TrainingCheckpoint]) -> str:
    """
    Export checkpoint ledger as newline-delimited JSON.
    
    Args:
        checkpoints: List of training checkpoints
    
    Returns:
        NDJSON string (one checkpoint per line)
    """
    lines = []
    for ckpt in checkpoints:
        ckpt_dict = asdict(ckpt)
        lines.append(json.dumps(ckpt_dict, sort_keys=True))
    
    return '\n'.join(lines)


# Example usage and tests
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("="*60)
    print("  Training Checkpoint Ledger - Test")
    print("="*60)
    
    # Simulate training checkpoints
    torch.manual_seed(42)
    
    checkpoints = []
    prev_hash = None
    
    for step in [0, 10, 20, 30]:
        # Simulate training state
        loss = 1.0 - (step * 0.01)
        eigenvalues = torch.tensor([295.0, 285.0, 275.0, 265.0], dtype=torch.float16)
        lora_A = torch.randn(512, 16, dtype=torch.float16)
        lora_B = torch.randn(16, 512, dtype=torch.float16)
        
        # Create checkpoint
        # Create checkpoint
        ckpt = create_training_checkpoint(
            step=step,
            loss=loss,
            eigenvalues=eigenvalues,
            lora_A=lora_A,
            lora_B=lora_B,
            prev_hash=prev_hash,
            rank=16,
            alpha=16.0,
            agent=None # Test without agent for now
        )
        
        checkpoints.append(ckpt)
        prev_hash = ckpt.checkpoint_hash
        
        print(f"\nStep {step}:")
        print(f"  Loss: {loss:.4f} -> {ckpt.loss_scaled}")
        print(f"  Hash: {ckpt.checkpoint_hash[:32]}...")
        print(f"  Prev: {ckpt.prev_checkpoint_hash[:16] if ckpt.prev_checkpoint_hash else 'genesis'}...")
    
    # Verify chain
    print(f"\n{'='*60}")
    is_valid = verify_checkpoint_chain(checkpoints)
    
    if is_valid:
        print("[PASS] Checkpoint chain verified!")
    else:
        print("[FAIL] Chain verification failed!")
    
    #Export to NDJSON
    print(f"\nExporting to NDJSON...")
    ndjson = export_ledger_ndjson(checkpoints)
    print(f"  Lines: {len(ndjson.splitlines())}")
    print(f"  First checkpoint:")
    print(f"    {ndjson.splitlines()[0][:100]}...")
    
    print("\n" + "="*60)
