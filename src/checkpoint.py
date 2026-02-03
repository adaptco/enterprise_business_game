"""
Content-Addressed Checkpoint System
Implements IPFS-style CID-based state persistence with Merkle lineage.
"""

import hashlib
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass


@dataclass
class CheckpointMetadata:
    """Metadata for a game state checkpoint"""
    checkpoint_id: str  # CID (content identifier)
    tick: int
    timestamp: str
    game_seed: int
    prev_checkpoint_cid: Optional[str]
    state_hash: str
    ledger_root: str


class CheckpointStore:
    """Base class for checkpoint storage backends"""
    
    def save_checkpoint(self, checkpoint: Dict[str, Any]) -> str:
        """Save checkpoint and return CID"""
        raise NotImplementedError
    
    def load_checkpoint(self, cid: str) -> Dict[str, Any]:
        """Load checkpoint by CID"""
        raise NotImplementedError
    
    def verify_checkpoint(self, checkpoint: Dict[str, Any]) -> bool:
        """Verify checkpoint integrity"""
        raise NotImplementedError


class LocalCheckpointStore(CheckpointStore):
    """
    Local filesystem checkpoint storage.
    Content-addressed: checkpoint files named by their CID.
    """
    
    def __init__(self, base_path: str = './checkpoints'):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
    
    def save_checkpoint(self, checkpoint: Dict[str, Any]) -> str:
        """Save checkpoint to local file"""
        # Compute CID
        cid = compute_checkpoint_cid(checkpoint)
        checkpoint["checkpoint_id"] = cid
        
        # Save to file (named by CID)
        filepath = os.path.join(self.base_path, f"{cid}.json")
        
        with open(filepath, 'w') as f:
            json.dump(checkpoint, f, sort_keys=True, indent=2)
        
        return cid
    
    def load_checkpoint(self, cid: str) -> Dict[str, Any]:
        """Load checkpoint by CID"""
        filepath = os.path.join(self.base_path, f"{cid}.json")
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Checkpoint not found: {cid}")
        
        with open(filepath, 'r') as f:
            checkpoint = json.load(f)
        
        # Verify CID matches content
        if not self.verify_checkpoint(checkpoint):
            raise ValueError(f"Checkpoint CID mismatch: {cid}")
        
        return checkpoint
    
    def verify_checkpoint(self, checkpoint: Dict[str, Any]) -> bool:
        """Verify checkpoint CID matches content"""
        claimed_cid = checkpoint.get("checkpoint_id")
        if not claimed_cid:
            return False
        
        # Recompute CID from content
        computed_cid = compute_checkpoint_cid(checkpoint)
        
        return claimed_cid == computed_cid
    
    def list_checkpoints(self) -> list[str]:
        """List all checkpoint CIDs"""
        files = os.listdir(self.base_path)
        return [f.replace('.json', '') for f in files if f.endswith('.json')]


def compute_checkpoint_cid(checkpoint: Dict[str, Any]) -> str:
    """
    Compute content identifier (CID) for checkpoint.
    Uses SHA-256 hash of canonical JSON representation.
    
    Format: "ckpt_<sha256_prefix>"
    (Simplified CID - full IPFS multihash coming in future version)
    """
    # Extract payload (exclude CID itself if present)
    payload = {
        "tick": checkpoint["tick"],
        "timestamp": checkpoint["timestamp"],
        "game_seed": checkpoint["game_seed"],
        "state_vector": checkpoint["state_vector"],
        "merkle_proof": checkpoint["merkle_proof"]
    }
    
    # Canonical JSON serialization (determinism contract)
    canonical_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    
    # SHA-256 hash
    digest = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
    
    # CID format: "ckpt_" prefix + first 32 chars of hash
    cid = f"ckpt_{digest[:32]}"
    
    return cid


def create_checkpoint(
    game_engine,
    prev_cid: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a checkpoint capsule from current game state.
    Returns checkpoint dict ready for storage.
    
    IMPORTANT: All numeric values are integers for canonical hash compatibility.
    - USD values stored as cents (multiply by 100)
    - Percentages stored as basis points (multiply by 100)
    - Metrics scaled by 100
    """
    from game_engine import Company
    
    # Collect company snapshots (integer-only)
    company_snapshots = []
    for company in game_engine.companies.values():
        snapshot = {
            "company_id": company.company_id,
            "company_name": company.company_name,
            "resources": {
                "employees": company.resources.employees,
                "cash_cents": int(company.resources.cash_usd * 100),  # USD → cents
                "inventory_units": company.resources.inventory_units,
                "equipment_value_cents": int(company.resources.equipment_value_usd * 100)
            },
            "financial": {
                "total_revenue_cents": int(company.financial.total_revenue_usd * 100),
                "total_expenses_cents": int(company.financial.total_expenses_usd * 100),
                "current_tick_revenue_cents": int(company.financial.current_tick_revenue * 100),
                "current_tick_expenses_cents": int(company.financial.current_tick_expenses * 100)
            },
            "metrics": {
                "market_share_bp": int(company.metrics.market_share_pct * 100),  # pct → basis points
                "brand_value_scaled": int(company.metrics.brand_value * 100),
                "employee_productivity_scaled": int(company.metrics.employee_productivity * 100)
            },
            "ledger_hash": company.ledger.get_latest_hash() or "genesis",
            "ledger_transactions": len(company.ledger.transactions)
        }
        company_snapshots.append(snapshot)
    
    # Market conditions (integer-only)
    market_conditions = {
        "demand_multiplier_scaled": int(game_engine.market_conditions.demand_multiplier * 1000),  # 3 decimal precision
        "interest_rate_bp": int(game_engine.market_conditions.interest_rate_pct * 100),
        "labor_cost_cents": int(game_engine.market_conditions.labor_cost_per_employee_usd * 100),
        "raw_material_cost_cents": int(game_engine.market_conditions.raw_material_cost_usd * 100),
        "consumer_confidence_index": int(game_engine.market_conditions.consumer_confidence_index),
        "regulatory_burden_scaled": int(game_engine.market_conditions.regulatory_burden * 1000)
    }
    
    # Build checkpoint
    checkpoint = {
        "tick": game_engine.current_tick,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "game_seed": game_engine.seed,
        
        "state_vector": {
            "market_conditions": market_conditions,
            "companies": company_snapshots
        },
        
        "merkle_proof": {
            "prev_checkpoint_cid": prev_cid,
            "state_hash": compute_state_hash(game_engine),
            "ledger_root": compute_ledger_merkle_root(game_engine)
        },
        
        "replay_metadata": {
            "resume_token": f"tick_{game_engine.current_tick}",
            "determinism_flags": {
                "rng_seed": game_engine.seed,
                "floating_point_mode": "integers_only",
                "usd_scaling": "cents_x100",
                "percentage_scaling": "basis_points_x100"
            }
        }
    }
    
    return checkpoint


def compute_state_hash(game_engine) -> str:
    """Compute SHA-256 hash of complete game state"""
    state = {
        "tick": game_engine.current_tick,
        "seed": game_engine.seed,
        "market": game_engine.market_conditions.to_dict(),
        "companies": [c.to_dict() for c in game_engine.companies.values()]
    }
    
    canonical_json = json.dumps(state, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()


def compute_ledger_merkle_root(game_engine) -> str:
    """
    Compute Merkle root of all company ledgers.
    Simple implementation: hash of all ledger hashes.
    """
    ledger_hashes = []
    
    for company in sorted(game_engine.companies.values(), key=lambda c: c.company_id):
        latest_hash = company.ledger.get_latest_hash()
        if latest_hash:
            ledger_hashes.append(latest_hash)
    
    # Combine all ledger hashes
    combined = ''.join(ledger_hashes)
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()


def replay_from_checkpoint(
    cid: str,
    store: CheckpointStore
):
    """
    Deterministic replay: reconstruct game state from checkpoint CID.
    Returns initialized GameEngine with restored state.
    """
    from game_engine import GameEngine, MarketConditions, Company, CompanyResources, FinancialState, PerformanceMetrics
    from ledger import CompanyLedger
    
    # Load checkpoint
    checkpoint = store.load_checkpoint(cid)
    
    # Verify integrity
    if not store.verify_checkpoint(checkpoint):
        raise ValueError(f"Checkpoint {cid} failed integrity verification!")
    
    # Create game engine with original seed
    game = GameEngine(seed=checkpoint["game_seed"])
    game.current_tick = checkpoint["tick"]
    
    # Restore market conditions
    market_data = checkpoint["state_vector"]["market_conditions"]
    game.market_conditions = MarketConditions(**market_data)
    
    # Restore companies
    for company_data in checkpoint["state_vector"]["companies"]:
        # Create company object
        company = Company(
            company_id=company_data["company_id"],
            company_name=company_data["company_name"],
            founding_capital_usd=0,  # Will be overwritten
            industry_sector=game_engine.IndustrySector.TECH,  # Default
            sovereign_signature="restored",
            is_ai=False
        )
        
        # Restore resources
        company.resources = CompanyResources(**company_data["resources"])
        
        # Restore financial state
        financial_data = company_data["financial"]
        company.financial = FinancialState()
        company.financial.total_revenue_usd = financial_data["total_revenue_usd"]
        company.financial.total_expenses_usd = financial_data["total_expenses_usd"]
        
        # Restore metrics
        company.metrics = PerformanceMetrics(**company_data["metrics"])
        
        # Note: Full ledger restoration would require separate ledger checkpoints
        company.ledger = CompanyLedger(company.company_id)
        
        company.current_tick = checkpoint["tick"]
        game.companies[company.company_id] = company
    
    # Verify restored state hash matches checkpoint
    restored_hash = compute_state_hash(game)
    original_hash = checkpoint["merkle_proof"]["state_hash"]
    
    if restored_hash != original_hash:
        raise ValueError(f"State hash mismatch! Original: {original_hash}, Restored: {restored_hash}")
    
    return game


def verify_checkpoint_chain(
    cid: str,
    store: CheckpointStore,
    genesis_cid: Optional[str] = None
) -> bool:
    """
    Verify Merkle chain integrity from CID back to genesis.
    Returns True if chain is intact.
    """
    current_cid = cid
    visited = set()
    
    while current_cid:
        if current_cid in visited:
            raise ValueError(f"Circular reference detected: {current_cid}")
        
        visited.add(current_cid)
        
        # Load checkpoint
        checkpoint = store.load_checkpoint(current_cid)
        
        # Verify integrity
        if not store.verify_checkpoint(checkpoint):
            return False
        
        # Get previous CID
        prev_cid = checkpoint["merkle_proof"]["prev_checkpoint_cid"]
        
        # If we reached genesis
        if prev_cid is None:
            if genesis_cid and current_cid != genesis_cid:
                return False  # Wrong genesis
            return True  # Chain complete
        
        current_cid = prev_cid
    
    return True
