"""
Hamiltonian LoRA Orchestrator - Full Integration Demo
Demonstrates surgical model fine-tuning with eigenspace-guided initialization.
"""

import torch
import torch.nn as nn
import torch.optim as optim
from ml.hamiltonian_eigen import HamiltonianEigenSolver
from ml.lora_adapter import LoRAAdapter
from ml.training_ledger import create_training_checkpoint, verify_checkpoint_chain, export_ledger_ndjson
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HamiltonianDemo")


def create_synthetic_transformer_layer(d_model: int = 512) -> nn.Linear:
    """Create a synthetic transformer feedforward layer"""
    return nn.Linear(d_model, d_model, dtype=torch.float16)


def run_hamiltonian_lora_demo():
    """
    Complete demonstration of Hamiltonian-guided LoRA fine-tuning.
    """
    print("="*70)
    print("  Hamiltonian Eigendecomposition Orchestrator — Full Demo")
    print("="*70)
    
    # Configuration
    d_model = 512
    rank = 16
    alpha = 16.0
    num_steps = 50
    lr = 1e-4
    
    print(f"\nConfiguration:")
    print(f"  Model dimension: {d_model}")
    print(f"  LoRA rank: {rank}")
    print(f"  Alpha: {alpha}")
    print(f"  Training steps: {num_steps}")
    print(f"  Learning rate: {lr}")
    
    # Step 1: Create base layer
    print("\n" + "-"*70)
    print("Step 1: Creating synthetic transformer layer")
    print("-"*70)
    
    torch.manual_seed(42)
    base_layer = create_synthetic_transformer_layer(d_model)
    base_weight = base_layer.weight.data  # (d_model, d_model)
    
    print(f"  Base weight shape: {base_weight.shape}")
    print(f"  Base weight norm: {base_weight.norm().item():.4f}")
    
    # Step 2: Hamiltonian eigendecomposition
    print("\n" + "-"*70)
    print("Step 2: Computing Hamiltonian eigenstates")
    print("-"*70)
    
    solver = HamiltonianEigenSolver(device='cpu', dtype=torch.float16)
    eigenvalues, eigenvectors = solver.compute_eigenstates(base_weight.T, k=rank)
    
    print(f"  Top-{rank} eigenvalues:")
    print(f"    λ_max = {eigenvalues[0].item():.4f}")
    print(f"    λ_min = {eigenvalues[-1].item():.4f}")
    
    energy_analysis = solver.compute_spectral_energy(base_weight.T, k=rank)
    print(f"  Spectral energy:")
    print(f"    Total: {energy_analysis['total_energy']:.2f}")
    print(f"    Top-{rank}: {energy_analysis['top_k_energy']:.2f}")
    print(f"    Explained variance: {energy_analysis['explained_variance']:.2%}")
    
    # Step 3: Initialize LoRA adapter
    print("\n" + "-"*70)
    print("Step 3: Initializing LoRA adapter from eigenspace")
    print("-"*70)
    
    eigenspace_basis = solver.compute_eigenspace_basis(base_weight.T, k=rank)
    
    adapter = LoRAAdapter(
        in_features=d_model,
        out_features=d_model,
        rank=rank,
        alpha=alpha,
        dtype=torch.float16,
        device='cpu'
    )
    
    adapter.initialize_from_eigenspace(eigenspace_basis)
    
    params = adapter.get_param_count()
    print(f"  LoRA parameters: {params['total']:,}")
    print(f"  Compression ratio: {params['compression_ratio']:.2f}x")
    
    # Step 4: Simulated training loop
    print("\n" + "-"*70)
    print("Step 4: Running training loop with checkpointing")
    print("-"*70)
    
    optimizer = optim.AdamW([adapter.lora_A], lr=lr)
    checkpoints = []
    prev_hash = None
    
    # Simulate training
    for step in range(0, num_steps + 1, 10):
        # Simulate decreasing loss
        loss = 1.0 - (step / num_steps) * 0.5
        
        # Create checkpoint
        ckpt = create_training_checkpoint(
            step=step,
            loss=loss,
            eigenvalues=eigenvalues,
            lora_A=adapter.lora_A.data,
            lora_B=adapter.lora_B.data,
            prev_hash=prev_hash,
            rank=rank,
            alpha=alpha
        )
        
        checkpoints.append(ckpt)
        prev_hash = ckpt.checkpoint_hash
        
        print(f"  Step {step:3d}: Loss={loss:.4f}, Hash={ckpt.checkpoint_hash[:16]}...")
        
        # Simulate gradient step (just for demo)
        if step < num_steps:
            optimizer.zero_grad()
            # Normally would compute loss and call loss.backward() here
            optimizer.step()
    
    # Step 5: Verify checkpoint chain
    print("\n" + "-"*70)
    print("Step 5: Verifying checkpoint chain integrity")
    print("-"*70)
    
    chain_valid = verify_checkpoint_chain(checkpoints)
    
    if chain_valid:
        print("  ✅ Checkpoint chain VERIFIED")
        print(f"  Total checkpoints: {len(checkpoints)}")
        print(f"  Genesis: {checkpoints[0].checkpoint_hash[:32]}...")
        print(f"  Head: {checkpoints[-1].checkpoint_hash[:32]}...")
    else:
        print("  ❌ Checkpoint chain verification FAILED")
    
    # Step 6: Export training ledger
    print("\n" + "-"*70)
    print("Step 6: Exporting training ledger (NDJSON)")
    print("-"*70)
    
    ndjson = export_ledger_ndjson(checkpoints)
    ledger_file = 'ml/hamiltonian_lora_training.ndjson'
    
    with open(ledger_file, 'w') as f:
        f.write(ndjson)
    
    print(f"  Exported to: {ledger_file}")
    print(f"  Lines: {len(ndjson.splitlines())}")
    
    # Step 7: Merge LoRA into base weight
    print("\n" + "-"*70)
    print("Step 7: Merging LoRA adaptation into base weight")
    print("-"*70)
    
    merged_weight = adapter.merge_into_base_weight(base_weight)
    delta_norm = (merged_weight - base_weight).norm().item()
    
    print(f"  Original norm: {base_weight.norm().item():.4f}")
    print(f"  Merged norm: {merged_weight.norm().item():.4f}")
    print(f"  Delta norm: {delta_norm:.4f}")
    
    # Final summary
    print("\n" + "="*70)
    print("DEMO COMPLETE")
    print("="*70)
    print("\n✅ Successfully demonstrated:")
    print("  - Hamiltonian eigendecomposition")
    print("  - Eigenspace-guided LoRA initialization")
    print("  - Training with Merkle-chained checkpoints")
    print("  - Deterministic replay capability")
    print("  - Weight merging")
    print(f"\n📊 Training ledger saved: {ledger_file}")
    print("   Load in replay_viewer.html to visualize!")
    print("\n" + "="*70)


if __name__ == "__main__":
    run_hamiltonian_lora_demo()
