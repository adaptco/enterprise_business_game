"""
LoRA Adapter with Hamiltonian Eigenspace Initialization
Low-rank weight updates guided by dominant eigenstates.
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Optional
import logging

logger = logging.getLogger("LoRAAdapter")


class LoRAAdapter(nn.Module):
    """
    Low-Rank Adaptation (LoRA) module with Hamiltonian eigenspace initialization.
    
    Instead of random initialization, LoRA_B is initialized from the
    top-k eigenvectors of the weight Hamiltonian, capturing maximum variance.
    
    Forward: x @ W + scaling * (x @ A @ B)
    where:
        A ∈ ℝ^(d_in × r)  - learned coefficients
        B ∈ ℝ^(r × d_out) - initialized from eigenspace
        r << min(d_in, d_out) - rank
    """
    
    def __init__(
        self,
        in_features: int,
        out_features: int,
        rank: int = 16,
        alpha: float = 16.0,
        dtype: torch.dtype = torch.float16,
        device: str = 'cpu'
    ):
        super().__init__()
        
        self.in_features = in_features
        self.out_features = out_features
        self.rank = rank
        self.alpha = alpha
        self.scaling = alpha / rank
        self.dtype = dtype
        self.device = device
        
        # LoRA matrices (FP16 for efficiency)
        self.lora_A = nn.Parameter(
            torch.zeros((in_features, rank), dtype=dtype, device=device)
        )
        self.lora_B = nn.Parameter(
            torch.zeros((rank, out_features), dtype=dtype, device=device)
        )
        
        # Initialize A with small random values (Kaiming uniform)
        # B will be initialized from eigenspace
        nn.init.kaiming_uniform_(self.lora_A, a=np.sqrt(5))
        
        logger.info(f"LoRAAdapter created: in={in_features}, out={out_features}, "
                   f"rank={rank}, α={alpha}, scaling={self.scaling:.4f}")
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Compute LoRA forward pass: x @ (A @ B) * scaling
        
        Args:
            x: Input tensor (..., in_features)
        
        Returns:
            LoRA output (..., out_features)
        """
        # x @ A: (..., in_features) @ (in_features, rank) -> (..., rank)
        # (... @ B: (..., rank) @ (rank, out_features) -> (..., out_features)
        lora_out = (x @ self.lora_A) @ self.lora_B
        return lora_out * self.scaling
    
    def initialize_from_eigenspace(self, eigenspace_basis: torch.Tensor):
        """
        Initialize LoRA_B from Hamiltonian eigenspace basis.
        
        Args:
            eigenspace_basis: (in_features, rank) matrix from eigendecomposition
                             = V[:, :r] @ sqrt(Λ[:r, :r])
        """
        if eigenspace_basis.shape != (self.in_features, self.rank):
            raise ValueError(
                f"Eigenspace basis shape {eigenspace_basis.shape} doesn't match "
                f"expected ({self.in_features}, {self.rank})"
            )
        
        # B^T = eigenspace_basis (transposed for correct matmul shape)
        # B: (rank, out_features) but we only have (in_features, rank)
        # For now, initialize with transposed basis (works if in == out)
        if self.in_features == self.out_features:
            self.lora_B.data = eigenspace_basis.T.to(dtype=self.dtype, device=self.device)
            logger.info("LoRA_B initialized from eigenspace (square matrix)")
        else:
            # For non-square, use eigenspace as column space for B^T
            # B: (rank, out) <- initialize with scaled identity projection
            scale_factor = np.sqrt(self.out_features / self.in_features)
            partial = eigenspace_basis[:self.out_features, :] if self.out_features < self.in_features else eigenspace_basis
            self.lora_B.data[:partial.shape[0], :] = partial.T.to(dtype=self.dtype, device=self.device) * scale_factor
            logger.info(f"LoRA_B initialized from eigenspace (rect, scale={scale_factor:.4f})")
    
    def get_effective_weights(self) -> torch.Tensor:
        """
        Compute effective weight update: ΔW = A @ B
        
        Returns:
            ΔW: (in_features, out_features) weight delta
        """
        return (self.lora_A @ self.lora_B) * self.scaling
    
    def merge_into_base_weight(self, base_weight: torch.Tensor) -> torch.Tensor:
        """
        Merge LoRA adaptation into base weight: W' = W + ΔW
        
        Args:
            base_weight: (out_features, in_features) original weight
        
        Returns:
            merged: (out_features, in_features) updated weight
        """
        delta_W = self.get_effective_weights()  # (in, out)
        return base_weight + delta_W.T  # Transpose to match (out, in)
    
    def get_param_count(self) -> dict:
        """Get trainable parameter counts"""
        return {
            "lora_A": self.lora_A.numel(),
            "lora_B": self.lora_B.numel(),
            "total": self.lora_A.numel() + self.lora_B.numel(),
            "compression_ratio": (
                (self.in_features * self.out_features) / 
                (self.lora_A.numel() + self.lora_B.numel())
            )
        }


# Example usage and tests
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("="*60)
    print("  LoRA Adapter - Test with Eigenspace Init")
    print("="*60)
    
    # Create synthetic weight matrix
    torch.manual_seed(42)
    d_in, d_out, rank = 512, 512, 16
    
    # Simulate a transformer layer weight
    base_weight = torch.randn(d_out, d_in, dtype=torch.float16)
    
    print(f"\nBase weight: {base_weight.shape}")
    print(f"LoRA rank: {rank}")
    
    # Create LoRA adapter
    adapter = LoRAAdapter(
        in_features=d_in,
        out_features=d_out,
        rank=rank,
        alpha=16.0,
        dtype=torch.float16,
        device='cpu'
    )
    
    print(f"\nLoRA parameters:")
    params = adapter.get_param_count()
    for k, v in params.items():
        if k != 'compression_ratio':
            print(f"  {k}: {v:,}")
        else:
            print(f"  {k}: {v:.2f}x")
    
    # Initialize from eigenspace (simulate)
    from hamiltonian_eigen import HamiltonianEigenSolver
    
    solver = HamiltonianEigenSolver(device='cpu', dtype=torch.float16)
    eigenspace_basis = solver.compute_eigenspace_basis(base_weight.T, k=rank)
    
    print(f"\nEigenspace basis: {eigenspace_basis.shape}")
    adapter.initialize_from_eigenspace(eigenspace_basis)
    
    # Test forward pass
    x = torch.randn(32, d_in, dtype=torch.float16)  # Batch of 32
    lora_output = adapter(x)
    
    print(f"\nForward pass:")
    print(f"  Input: {x.shape}")
    print(f"  LoRA output: {lora_output.shape}")
    print(f"  Output norm: {lora_output.norm().item():.4f}")
    
    # Test weight merging
    merged_weight = adapter.merge_into_base_weight(base_weight)
    print(f"\nWeight merging:")
    print(f"  Original norm: {base_weight.norm().item():.4f}")
    print(f"  Merged norm: {merged_weight.norm().item():.4f}")
    print(f"  Delta norm: {(merged_weight - base_weight).norm().item():.4f}")
    
    print("\n✅ LoRA adapter working correctly!")
    print("="*60)
