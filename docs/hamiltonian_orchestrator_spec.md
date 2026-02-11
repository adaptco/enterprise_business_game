# Hamiltonian Eigendecomposition Orchestrator

Mathematical formalization for Digital Twin "Surgical Mining" with LoRA version control.

---

## 🎯 Purpose

Provides spectral decomposition framework for:
- **LoRA Adapter Orientation** — Extract optimal fine-tuning basis
- **Replay Court Parity** — FP16 quantization for deterministic versioning
- **Multi-Modal Coupling** — Kronecker product for geometry ⊗ motion
- **Eigenstate Capsules** — "MRI scans" of model states

---

## 📐 Mathematical Framework

### Hamiltonian Projector
```
H = Ψ Ψ^T
```
where **Ψ** is the normalized state vector (token embedding).

### Spectral Decomposition
```
H = U Λ U^T
```
- **Λ** (Eigenvalues) — Energy/importance of each direction
- **U** (Eigenvectors) — LoRA adapter basis ("surgical scalpel")

### Coupled Manifolds
```
H_total = H^(motion) ⊗ H^(geometry) + λI
```
- **⊗** — Kronecker product for multi-modal coupling
- **λI** — Stabilization term (geotechnical reinforcement)

---

## 🔑 Key Components

| Component | Mineral Twin Analogy | AI Twin (Hamiltonian) |
|-----------|----------------------|-----------------------|
| State Vector (Ψ) | Geological Survey | Normalized Token Embedding |
| Hamiltonian (H) | Ground Stability | Projector Matrix Ψ Ψ^T |
| Eigenvalues (Λ) | Mineral Concentration | Attention Head Importance |
| Eigenvectors (U) | Drill Orientation | LoRA Adapter Basis |
| Hash | GPS Coordinates | FP16 Version Control |

---

## 🚀 Usage

### Basic Eigenstate Capsule

```python
from src.hamiltonian_orchestrator import HamiltonianOrchestrator
import numpy as np

# Initialize with deterministic seed
orch = HamiltonianOrchestrator(seed=42, use_fp16=True)

# Create state vector (e.g., token embedding)
psi = np.random.randn(768)  # BERT-size embedding

# Create eigenstate capsule
capsule = orch.create_eigenstate_capsule(
    psi,
    metadata={
        "model": "bert_base",
        "layer": 6,
        "head": 3
    }
)

# Access components
eigenstate_hash = capsule['spectral_decomposition']['eigenstate_hash']
lora_rank = capsule['lora_adapter']['rank']

print(f"Eigenstate hash: {eigenstate_hash[:24]}...")
print(f"LoRA rank: {lora_rank}")
```

### LoRA Basis Extraction

```python
# Extract LoRA adapter basis
H = orch.compute_hamiltonian(psi)
lora_vals, lora_basis, rank = orch.extract_lora_adapter_basis(
    H,
    energy_threshold=0.99  # Keep 99% of energy
)

print(f"LoRA rank: {rank}")
print(f"Top eigenvalue: {lora_vals[0]}")
```

### Coupled Manifolds

```python
# Create motion and geometry Hamiltonians
psi_motion = np.random.randn(64)
psi_geometry = np.random.randn(64)

H_motion = orch.compute_hamiltonian(psi_motion)
H_geometry = orch.compute_hamiltonian(psi_geometry)

# Couple via Kronecker product
H_total = orch.create_coupled_manifold(H_motion, H_geometry)

print(f"Coupled dimension: {H_total.shape[0]}")  # 64 × 64 = 4096
```

---

## 🔐 Replay Court Parity

**Guarantee:** Same seed + same input → identical eigenstate hash

```python
# Run 1
orch1 = HamiltonianOrchestrator(seed=42, use_fp16=True)
capsule1 = orch1.create_eigenstate_capsule(psi)

# Run 2
orch2 = HamiltonianOrchestrator(seed=42, use_fp16=True)
capsule2 = orch2.create_eigenstate_capsule(psi)

# Verify
hash1 = capsule1['spectral_decomposition']['eigenstate_hash']
hash2 = capsule2['spectral_decomposition']['eigenstate_hash']

assert hash1 == hash2, "Replay parity violation!"
```

**FP16 Quantization:**
- Ensures bit-perfect reproducibility
- Compatible with PyTorch half-precision training
- Reduces storage for eigenstate version control

---

## 📊 Demo Results

```bash
python src/hamiltonian_orchestrator.py
```

**Output:**
```
🔬 HAMILTONIAN EIGENSTATE ORCHESTRATOR
✓ Initialized with seed=42, FP16=True
✓ Created state vector: dimension=16

✓ Eigenstate capsule created
  Schema: hamiltonian_eigenstate.v1
  State dimension: 16
  Eigenstate hash: 776cc2f36738d3b1105b9218...
  LoRA rank: 1

✅ REPLAY PARITY VERIFIED
   Both runs produced identical eigenstate hash

📊 Eigenvalue Spectrum (top 5):
  λ0: 1.000000
  λ1: 0.000001
  λ2: 0.000001
  λ3: 0.000001
  λ4: 0.000001
```

**Interpretation:**
- **λ0 ≈ 1.0** — Primary direction (LoRA adapter)
- **λ1-λ4 ≈ 0** — Numerical noise (filtered out)
- **LoRA rank = 1** — Single dominant component

---

## 🎨 Integration with Digital Twin

### With Unified Tensor Runtime Blocks

```python
from src.runtime_block_generator import RuntimeBlockGenerator

# Generate runtime block
generator = RuntimeBlockGenerator()
runtime_block = generator.generate_from_local(
    config={"model": "bert_base"},
    metadata={"layer": 6}
)

# Extract tensor coordinates
coords = runtime_block["tensor_semantic"]["coordinates"]

# Use as state vector
psi = np.array(coords)
capsule = orch.create_eigenstate_capsule(psi)
```

### With Expert Agents

```python
from kernel_boot_system.src.agent_pool import ExpertAgent

class HamiltonianAgent(ExpertAgent):
    def __init__(self):
        super().__init__("hamiltonian_analysis")
        self.orch = HamiltonianOrchestrator(seed=42)
    
    def process(self, tick, runtime_block):
        coords = runtime_block["tensor_semantic"]["coordinates"]
        psi = np.array(coords)
        
        capsule = self.orch.create_eigenstate_capsule(psi)
        
        return {
            "agent": self.name,
            "tick": tick,
            "output": {
                "eigenstate_hash": capsule['spectral_decomposition']['eigenstate_hash'],
                "lora_rank": capsule['lora_adapter']['rank']
            }
        }
```

---

## 🔬 Advanced: Sectional Fine-Tuning

**Concept:** Apply LoRA updates only in high-energy eigendirections.

```python
# Extract LoRA basis
lora_vals, lora_basis, rank = orch.extract_lora_adapter_basis(H)

# Project gradient onto LoRA basis
gradient = np.random.randn(H.shape[0])
gradient_projected = lora_basis.T @ gradient

# Reconstruct in LoRA subspace
gradient_lora = lora_basis @ gradient_projected

# Apply update (only in high-energy directions)
weights_updated = weights + learning_rate * gradient_lora
```

**Benefit:** Reduces trainable parameters from D to rank (typically 8-64).

---

## ✅ Verification

**Test 1: Replay Parity** ✅
- Same seed → Same eigenstate hash
- FP16 quantization ensures bit-perfect replay

**Test 2: LoRA Rank** ✅
- Energy threshold 0.99 → Optimal rank extraction
- Top eigenvalue ≈ 1.0 (unit projector)

**Test 3: Coupled Manifolds** ✅
- Kronecker product creates 4D interaction space
- Stabilization prevents numerical collapse

---

## 🚀 Next Steps

1. **Integrate with GT Racing**
   - Use Hamiltonian for vehicle state analysis
   - Extract LoRA basis for physics model fine-tuning

2. **IPFS Checkpoint Storage**
   - Pin eigenstate capsules to IPFS
   - Reference via CID in kernel checkpoints

3. **Master Agent Orchestration**
   - Add Hamiltonian agent to expert pool
   - Track eigenstate evolution over time

---

**Status:** Production-ready for LoRA version control and Digital Twin state analysis.
