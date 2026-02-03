"""
Hamiltonian Eigendecomposition Orchestrator
Mathematical formalization for Digital Twin state manifolds with spectral analysis.

Based on: H = U Λ U^T decomposition for "Surgical Mining" of LLM states
- Eigenvalues (Λ): Mineral concentration / attention importance
- Eigenstates (U): Surgical scalpel / LoRA adapter orientation
- FP16 quantization: Replay-Court parity guarantee
"""

import numpy as np
import torch
import hashlib
import json
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass


@dataclass
class HamiltonianState:
    """
    State vector representation for Digital Twin manifold.
    Ψ (psi) represents the normalized token/state vector.
    """
    psi: np.ndarray  # Normalized state vector
    timestamp: str
    metadata: Dict[str, Any]


class HamiltonianOrchestrator:
    """
    Orchestrates Hamiltonian eigendecomposition for Digital Twin state analysis.
    
    Key concepts:
    - H = Ψ Ψ^T (outer product projector)
    - H = U Λ U^T (spectral decomposition)
    - Eigenvalues (Λ) = importance/energy of each direction
    - Eigenstates (U) = basis for LoRA adaptation
    """
    
    def __init__(self, seed: int = 42, use_fp16: bool = True):
        """
        Initialize orchestrator with deterministic seed.
        
        Args:
            seed: Random seed for reproducibility
            use_fp16: Use FP16 quantization for Replay Court parity
        """
        self.seed = seed
        self.use_fp16 = use_fp16
        self.dtype = torch.float16 if use_fp16 else torch.float32
        
        # Set deterministic seed
        np.random.seed(seed)
        torch.manual_seed(seed)
    
    def normalize_state_vector(self, psi: np.ndarray) -> np.ndarray:
        """
        Normalize state vector to unit length.
        
        Args:
            psi: Raw state vector
        
        Returns:
            Normalized Ψ with ||Ψ|| = 1
        """
        norm = np.linalg.norm(psi)
        if norm < 1e-10:
            raise ValueError("State vector has zero norm")
        return psi / norm
    
    def compute_hamiltonian(self, psi: np.ndarray) -> np.ndarray:
        """
        Compute Hamiltonian projector: H = Ψ Ψ^T
        
        This represents the "energy surface" of the state manifold.
        
        Args:
            psi: Normalized state vector (column vector)
        
        Returns:
            H: Hamiltonian matrix (projector onto Ψ)
        """
        psi = self.normalize_state_vector(psi)
        psi_col = psi.reshape(-1, 1)
        H = psi_col @ psi_col.T
        return H
    
    def spectral_decomposition(
        self,
        H: np.ndarray,
        stabilization: float = 1e-6
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Perform eigendecomposition: H = U Λ U^T
        
        Args:
            H: Hamiltonian matrix
            stabilization: λI term for numerical stability
        
        Returns:
            (eigenvalues, eigenvectors) sorted by descending eigenvalue
        """
        # Add stabilization term (geotechnical reinforcement)
        H_stable = H + stabilization * np.eye(H.shape[0])
        
        # Compute eigendecomposition (deterministic with fixed seed)
        eigenvalues, eigenvectors = np.linalg.eigh(H_stable)
        
        # Sort by descending eigenvalue (most important first)
        idx = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]
        
        return eigenvalues, eigenvectors
    
    def quantize_fp16(self, array: np.ndarray) -> np.ndarray:
        """
        Quantize to FP16 for Replay Court parity.
        
        Ensures bit-perfect reproducibility across runs.
        """
        if not self.use_fp16:
            return array
        
        # Convert to torch FP16, then back to numpy
        tensor = torch.tensor(array, dtype=torch.float16)
        return tensor.cpu().numpy().astype(np.float32)
    
    def compute_eigenstate_hash(
        self,
        eigenvalues: np.ndarray,
        eigenvectors: np.ndarray
    ) -> str:
        """
        Compute deterministic hash of eigenstate for version control.
        
        This creates a "save state" for LoRA adapter orientation.
        """
        # Quantize to FP16
        eigenvalues_q = self.quantize_fp16(eigenvalues)
        eigenvectors_q = self.quantize_fp16(eigenvectors)
        
        # Create canonical JSON
        state = {
            "eigenvalues": eigenvalues_q.tolist(),
            "eigenvectors": eigenvectors_q.tolist(),
            "seed": self.seed
        }
        
        canonical_json = json.dumps(state, sort_keys=True, separators=(',', ':'))
        hash_digest = hashlib.sha256(canonical_json.encode()).hexdigest()
        
        return hash_digest
    
    def create_coupled_manifold(
        self,
        H_motion: np.ndarray,
        H_geometry: np.ndarray,
        stabilization: float = 1e-6
    ) -> np.ndarray:
        """
        Create coupled manifold: H_total = H_motion ⊗ H_geometry
        
        This represents multi-modal interactions (e.g., prompt structure ↔ inference path).
        
        Args:
            H_motion: Hamiltonian for motion/inference dynamics
            H_geometry: Hamiltonian for geometry/prompt structure
            stabilization: Regularization term
        
        Returns:
            H_total: Coupled Hamiltonian via Kronecker product
        """
        H_coupled = np.kron(H_motion, H_geometry)
        
        # Add stabilization
        H_total = H_coupled + stabilization * np.eye(H_coupled.shape[0])
        
        return H_total
    
    def extract_lora_adapter_basis(
        self,
        H: np.ndarray,
        energy_threshold: float = 0.99
    ) -> Tuple[np.ndarray, np.ndarray, int]:
        """
        Extract LoRA adapter basis from Hamiltonian.
        
        Keeps only eigenvectors with cumulative energy > threshold.
        
        Args:
            H: Hamiltonian matrix
            energy_threshold: Fraction of energy to retain (0-1)
        
        Returns:
            (selected_eigenvalues, lora_basis, rank)
        """
        eigenvalues, eigenvectors = self.spectral_decomposition(H)
        
        # Compute cumulative energy
        total_energy = np.sum(eigenvalues)
        cumulative = np.cumsum(eigenvalues) / total_energy
        
        # Find rank (number of components to keep)
        rank = np.searchsorted(cumulative, energy_threshold) + 1
        
        # Extract LoRA basis (top-k eigenvectors)
        lora_eigenvalues = eigenvalues[:rank]
        lora_basis = eigenvectors[:, :rank]
        
        return lora_eigenvalues, lora_basis, rank
    
    def create_eigenstate_capsule(
        self,
        psi: np.ndarray,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create complete eigenstate capsule for Replay Court storage.
        
        This is the "MRI scan" of the model state.
        """
        from datetime import datetime, timezone
        
        # Normalize state
        psi_norm = self.normalize_state_vector(psi)
        
        # Compute Hamiltonian
        H = self.compute_hamiltonian(psi_norm)
        
        # Spectral decomposition
        eigenvalues, eigenvectors = self.spectral_decomposition(H)
        
        # Quantize for replay parity
        eigenvalues_q = self.quantize_fp16(eigenvalues)
        eigenvectors_q = self.quantize_fp16(eigenvectors)
        
        # Compute hash
        eigenstate_hash = self.compute_eigenstate_hash(eigenvalues_q, eigenvectors_q)
        
        # Extract LoRA rank
        lora_vals, lora_basis, rank = self.extract_lora_adapter_basis(H)
        
        # Create capsule
        capsule = {
            "schema": "hamiltonian_eigenstate.v1",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "seed": self.seed,
            "use_fp16": self.use_fp16,
            "state_vector": {
                "psi": psi_norm.tolist(),
                "dimension": len(psi_norm)
            },
            "hamiltonian": {
                "matrix_hash": hashlib.sha256(H.tobytes()).hexdigest()[:16]
            },
            "spectral_decomposition": {
                "eigenvalues": eigenvalues_q.tolist(),
                "eigenvectors": eigenvectors_q.tolist(),
                "eigenstate_hash": eigenstate_hash
            },
            "lora_adapter": {
                "rank": int(rank),
                "energy_threshold": 0.99,
                "selected_eigenvalues": lora_vals.tolist(),
                "basis_vectors": lora_basis.tolist()
            },
            "metadata": metadata or {}
        }
        
        return capsule


def demo_hamiltonian_orchestration():
    """Demonstration of Hamiltonian orchestration for Digital Twin."""
    print("\n" + "="*60)
    print("🔬 HAMILTONIAN EIGENSTATE ORCHESTRATOR")
    print("="*60)
    
    # Create orchestrator with deterministic seed
    orchestrator = HamiltonianOrchestrator(seed=42, use_fp16=True)
    print(f"✓ Initialized with seed={orchestrator.seed}, FP16={orchestrator.use_fp16}")
    
    # Create example state vector (e.g., token embedding)
    dimension = 16
    psi_raw = np.random.randn(dimension)
    print(f"\n✓ Created state vector: dimension={dimension}")
    
    # Create eigenstate capsule
    print("\n📦 Creating eigenstate capsule...")
    capsule = orchestrator.create_eigenstate_capsule(
        psi_raw,
        metadata={
            "model": "digital_twin_v1",
            "layer": "attention_head_3"
        }
    )
    
    print(f"\n✓ Eigenstate capsule created")
    print(f"  Schema: {capsule['schema']}")
    print(f"  State dimension: {capsule['state_vector']['dimension']}")
    print(f"  Eigenstate hash: {capsule['spectral_decomposition']['eigenstate_hash'][:24]}...")
    print(f"  LoRA rank: {capsule['lora_adapter']['rank']}")
    
    # Test deterministic replay
    print("\n🔁 Testing deterministic replay...")
    capsule2 = orchestrator.create_eigenstate_capsule(psi_raw)
    
    hash1 = capsule['spectral_decomposition']['eigenstate_hash']
    hash2 = capsule2['spectral_decomposition']['eigenstate_hash']
    
    if hash1 == hash2:
        print(f"✅ REPLAY PARITY VERIFIED")
        print(f"   Both runs produced identical eigenstate hash")
    else:
        print(f"❌ REPLAY PARITY FAILED")
    
    # Display eigenvalue spectrum
    eigenvalues = capsule['spectral_decomposition']['eigenvalues']
    print(f"\n📊 Eigenvalue Spectrum (top 5):")
    for i, val in enumerate(eigenvalues[:5]):
        print(f"  λ{i}: {val:.6f}")
    
    print("\n" + "="*60)
    print("✅ Hamiltonian orchestration complete")
    print("="*60)


if __name__ == "__main__":
    demo_hamiltonian_orchestration()
