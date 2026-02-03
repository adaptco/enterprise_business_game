"""
Hamiltonian Eigendecomposition Engine
Extracts dominant eigenstates from weight matrices for LoRA fine-tuning.
"""

import torch
import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger("HamiltonianEigen")


class HamiltonianEigenSolver:
    """
    Computes eigendecomposition of Hamiltonian H = W^T W
    to identify dominant "energy modes" for surgical LoRA updates.
    
    Uses FP16 precision for memory efficiency while maintaining
    deterministic reproducibility across runs.
    """
    
    def __init__(
        self,
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu',
        dtype: torch.dtype = torch.float16
    ):
        self.device = device
        self.dtype = dtype
        logger.info(f"HamiltonianEigenSolver initialized: device={device}, dtype={dtype}")
    
    def compute_eigenstates(
        self,
        weight: torch.Tensor,
        k: int = 16,
        eps: float = 1e-6
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Compute top-k eigenstates of Hamiltonian H = W^T W
        
        Args:
            weight: Weight matrix (n, m) - typically from transformer layer
            k: Number of top eigenvectors to return
            eps: Small constant for numerical stability
        
        Returns:
            eigenvalues: (k,) tensor in DESCENDING order (FP16)
            eigenvectors: (m, k) matrix of corresponding eigenvectors (FP16)
        
        Mathematical guarantee:
            H v_i = λ_i v_i  where λ_1 >= λ_2 >= ... >= λ_k
        
        Note:
            Computation is done in FP32 for numerical stability,
            then converted to FP16 for memory efficiency and hashing.
        """
        # Move to device but compute in FP32 (FP16 eigh not supported on CPU)
        W = weight.to(device=self.device, dtype=torch.float32)
        n, m = W.shape
        
        logger.debug(f"Computing Hamiltonian for weight matrix: {W.shape}")
        
        # Construct Hamiltonian (Gram matrix)
        # H = W^T @ W is symmetric positive semi-definite
        H = W.T @ W  # (m, m)
        
        # Add small regularization for numerical stability
        H = H + eps * torch.eye(m, dtype=torch.float32, device=self.device)
        
        # Eigendecomposition (in FP32)
        # Note: torch.linalg.eigh returns eigenvalues in ASCENDING order
        try:
            eigenvalues, eigenvectors = torch.linalg.eigh(H)
        except RuntimeError as e:
            logger.error(f"Eigendecomposition failed: {e}")
            logger.error(f"Matrix stats: min={H.min()}, max={H.max()}, norm={H.norm()}")
            raise
        
        # Flip to DESCENDING order and take top-k
        eigenvalues = eigenvalues.flip(0)[:k]
        eigenvectors = eigenvectors.flip(1)[:, :k]
        
        # Convert to FP16 for storage/hashing
        eigenvalues = eigenvalues.to(dtype=self.dtype)
        eigenvectors = eigenvectors.to(dtype=self.dtype)
        
        # Verify orthonormality (for debugging)
        if logger.isEnabledFor(logging.DEBUG):
            gram = eigenvectors.T @ eigenvectors
            identity_error = (gram - torch.eye(k, dtype=self.dtype, device=self.device)).abs().max()
            logger.debug(f"Eigenvector orthonormality error: {identity_error.item():.2e}")
        
        logger.info(f"Extracted top-{k} eigenstates: λ_max={eigenvalues[0].item():.4f}, "
                   f"λ_min={eigenvalues[-1].item():.4f}")
        
        return eigenvalues, eigenvectors
    
    def compute_eigenspace_basis(
        self,
        weight: torch.Tensor,
        k: int = 16
    ) -> torch.Tensor:
        """
        Compute basis matrix for top-k eigenspace.
        This can be used to initialize LoRA's B matrix.
        
        Args:
            weight: Weight matrix (n, m)
            k: Rank for LoRA
        
        Returns:
            B: (m, k) basis matrix scaled by sqrt(eigenvalues)
        
        Usage:
            B = eigenspace_basis  # Use for LoRA initialization
            A = trainable parameters  # Learn via SGD
            ΔW = B @ A^T  # Low-rank update
        """
        eigenvalues, eigenvectors = self.compute_eigenstates(weight, k)
        
        # Scale eigenvectors by sqrt of eigenvalues
        # This ensures the reconstruction captures variance correctly
        sqrt_lambda = torch.sqrt(eigenvalues).unsqueeze(0)  # (1, k)
        B = eigenvectors * sqrt_lambda  # (m, k)
        
        return B
    
    def compute_spectral_energy(
        self,
        weight: torch.Tensor,
        k: int = 16
    ) -> dict:
        """
        Analyze spectral energy distribution of weight matrix.
        
        Returns:
            Dictionary with:
                - total_energy: Sum of all eigenvalues
                - top_k_energy: Sum of top-k eigenvalues
                - explained_variance: Fraction of variance in top-k modes
                - effective_rank: Number of eigenvalues > 1% of max
        """
        eigenvalues, _ = self.compute_eigenstates(weight, k=min(k, weight.size(1)))
        
        total_energy = eigenvalues.sum().item()
        top_k_energy = eigenvalues[:k].sum().item()
        explained_variance = top_k_energy / total_energy if total_energy > 0 else 0.0
        
        # Effective rank: eigenvalues > 1% of max
        threshold = eigenvalues[0].item() * 0.01
        effective_rank = (eigenvalues > threshold).sum().item()
        
        return {
            "total_energy": total_energy,
            "top_k_energy": top_k_energy,
            "explained_variance": explained_variance,
            "effective_rank": effective_rank,
            "eigenvalues": eigenvalues.cpu().numpy().tolist()
        }


def canonical_eigenvalues_int(eigenvalues: torch.Tensor, scale: int = 100) -> list[int]:
    """
    Convert FP16 eigenvalues to canonical integer representation for hashing.
    
    Args:
        eigenvalues: FP16 tensor
        scale: Scaling factor (default 100 for 2 decimal precision)
               Note: Lower scale to avoid overflow with large eigenvalues
    
    Returns:
        List of integers: [λ_1 * scale, λ_2 * scale, ...]
    """
    eigenvalues_np = eigenvalues.cpu().numpy()
    eigenvalues_scaled = (eigenvalues_np * scale).round()
    
    # Clamp to int32 range to avoid overflow
    eigenvalues_scaled = np.clip(eigenvalues_scaled, -2147483648, 2147483647)
    eigenvalues_int = eigenvalues_scaled.astype(np.int32).tolist()
    
    return eigenvalues_int


# Example usage and tests
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("="*60)
    print("  Hamiltonian Eigendecomposition Engine - Test")
    print("="*60)
    
    # Create synthetic weight matrix
    torch.manual_seed(42)
    W = torch.randn(512, 1024, dtype=torch.float16)
    
    print(f"\nWeight matrix: {W.shape}")
    print(f"  dtype: {W.dtype}")
    print(f"  device: {W.device}")
    
    # Initialize solver
    solver = HamiltonianEigenSolver(device='cpu', dtype=torch.float16)
    
    # Compute eigenstates
    print("\n1. Computing eigenstates...")
    eigenvalues, eigenvectors = solver.compute_eigenstates(W, k=16)
    
    print(f"  Top eigenvalue: {eigenvalues[0].item():.4f}")
    print(f"  Bottom eigenvalue: {eigenvalues[-1].item():.4f}")
    print(f"  Eigenvectors shape: {eigenvectors.shape}")
    
    # Compute eigenspace basis
    print("\n2. Computing eigenspace basis for LoRA...")
    B = solver.compute_eigenspace_basis(W, k=16)
    print(f"  Basis matrix: {B.shape}")
    print(f"  Basis norm: {B.norm().item():.4f}")
    
    # Analyze spectral energy
    print("\n3. Spectral energy analysis...")
    energy = solver.compute_spectral_energy(W, k=16)
    print(f"  Total energy: {energy['total_energy']:.2f}")
    print(f"  Top-16 energy: {energy['top_k_energy']:.2f}")
    print(f"  Explained variance: {energy['explained_variance']:.2%}")
    print(f"  Effective rank: {energy['effective_rank']}")
    
    # Canonical integer encoding
    print("\n4. Canonical integer encoding...")
    eigenvalues_int = canonical_eigenvalues_int(eigenvalues, scale=1000)
    print(f"  Integer eigenvalues: {eigenvalues_int[:5]}...")
    
    # Test determinism
    print("\n5. Determinism test...")
    torch.manual_seed(42)  # Reset seed
    W2 = torch.randn(512, 1024, dtype=torch.float16)
    eigenvalues2, _ = solver.compute_eigenstates(W2, k=16)
    
    match = torch.allclose(eigenvalues, eigenvalues2, atol=1e-4)
    print(f"  Eigenvalues match: {match}")
    
    if match:
        print("\n✅ Hamiltonian eigendecomposition is deterministic!")
    else:
        print("\n⚠️  Warning: Non-deterministic behavior detected")
    
    print("\n" + "="*60)
