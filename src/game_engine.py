"""
Core game engine with deterministic tick progression.
Implements market simulation, company management, and SSOT integration.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import random

from ledger import CompanyLedger, Account, TransactionType
try:
    from ipfs_bridge import IPFSBridge, IPFSConfig
except ImportError:
    IPFSBridge = None
    IPFSConfig = None


class OperationType(Enum):
    """Business operation types"""
    HIRE = "HIRE"
    FIRE = "FIRE"
    PRODUCE = "PRODUCE"
    MARKET = "MARKET"
    R_AND_D = "R_AND_D"
    ACQUIRE = "ACQUIRE"
    INVEST = "INVEST"
    LOAN = "LOAN"


class IndustrySector(Enum):
    """Company industry sectors"""
    TECH = "TECH"
    MANUFACTURING = "MANUFACTURING"
    SERVICES = "SERVICES"
    FINANCE = "FINANCE"
    RETAIL = "RETAIL"
    ENERGY = "ENERGY"


@dataclass
class MarketConditions:
    """Global market economic conditions"""
    demand_multiplier: float = 1.0  # 1.0 = normal
    interest_rate_pct: float = 5.0
    labor_cost_per_employee_usd: float = 5000.0
    raw_material_cost_usd: float = 100.0
    consumer_confidence_index: float = 70.0  # 0-100
    regulatory_burden: float = 0.1  # 0-1

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class CompanyResources:
    """Company resource state"""
    employees: int = 0
    cash_usd: float = 0.0
    inventory_units: int = 0
    equipment_value_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FinancialState:
    """Company financial performance"""
    total_revenue_usd: float = 0.0
    total_expenses_usd: float = 0.0
    current_tick_revenue: float = 0.0
    current_tick_expenses: float = 0.0

    @property
    def net_income_usd(self) -> float:
        return self.total_revenue_usd - self.total_expenses_usd

    def to_dict(self) -> Dict[str, float]:
        return {
            **asdict(self),
            "net_income_usd": self.net_income_usd
        }


@dataclass
class PerformanceMetrics:
    """Business performance KPIs"""
    market_share_pct: float = 0.0
    brand_value: float = 0.0
    employee_productivity: float = 0.0

    @property
    def profit_margin_pct(self) -> float:
        """Calculate profit margin (for display only, computed from financial state)"""
        return 0.0  # Will be computed during ranking

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


class Company:
    """Represents a single company (shell company) in the simulation"""

    def __init__(
        self,
        company_id: str,
        company_name: str,
        founding_capital_usd: float,
        industry_sector: IndustrySector,
        sovereign_signature: str,
        is_ai: bool = False
    ):
        self.company_id = company_id
        self.company_name = company_name
        self.industry_sector = industry_sector
        self.sovereign_signature = sovereign_signature
        self.is_ai = is_ai

        # Initialize resources
        self.resources = CompanyResources(cash_usd=founding_capital_usd)
        self.financial = FinancialState()
        self.metrics = PerformanceMetrics()

        # Create ledger
        self.ledger = CompanyLedger(company_id)

        # Record initial investment as genesis transaction
        self.ledger.record_transaction(
            tick=0,
            from_company_id=None,  # External investment
            to_company_id=company_id,
            amount_usd=founding_capital_usd,
            transaction_type=TransactionType.INVESTMENT,
            debit_account=Account.CASH,
            credit_account=Account.EQUITY,
            metadata={"description": "Initial capital investment (genesis)"}
        )

        self.merkle_genesis_hash = self.ledger.get_genesis_hash()
        self.incorporation_timestamp = datetime.now(timezone.utc).isoformat()

        # State tracking
        self.current_tick = 0
        self.prev_state_hash: Optional[str] = None

    def compute_state_hash(self) -> str:
        """Compute SHA-256 hash of complete company state"""
        state = {
            "company_id": self.company_id,
            "tick": self.current_tick,
            "resources": self.resources.to_dict(),
            "financial_state": self.financial.to_dict(),
            "performance_metrics": self.metrics.to_dict()
        }
        canonical_json = json.dumps(state, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Export complete company state"""
        return {
            "company_id": self.company_id,
            "company_name": self.company_name,
            "tick": self.current_tick,
            "resources": self.resources.to_dict(),
            "financial_state": self.financial.to_dict(),
            "performance_metrics": self.metrics.to_dict(),
            "state_hash": self.compute_state_hash(),
            "prev_state_hash": self.prev_state_hash,
            "is_ai": self.is_ai
        }

    def registration_info(self) -> Dict[str, Any]:
        """Export company registration info (for initial capsule)"""
        return {
            "company_id": self.company_id,
            "company_name": self.company_name,
            "founding_capital_usd": self.resources.cash_usd,
            "incorporation_timestamp": self.incorporation_timestamp,
            "industry_sector": self.industry_sector.value,
            "sovereign_signature": self.sovereign_signature,
            "merkle_genesis_hash": self.merkle_genesis_hash
        }


class GameEngine:
    """
    Core simulation engine with deterministic tick progression.
    Manages companies, market state, and game loop.
    """

    def __init__(self, seed: int = 42, ipfs_bridge: Optional['IPFSBridge'] = None, auto_checkpoint_interval: Optional[int] = None):
        self.seed = seed
        random.seed(seed)  # For deterministic market fluctuations

        self.current_tick = 0
        self.companies: Dict[str, Company] = {}  # company_id -> Company
        self.market_conditions = MarketConditions()

        # Market state history (for Merkle chain)
        self.market_state_history: List[Dict[str, Any]] = []
        self.prev_market_hash: Optional[str] = None
        
        # Checkpoint support
        self.ipfs_bridge = ipfs_bridge
        self.checkpoint_history: List[Dict[str, Any]] = []
        self.auto_checkpoint_interval = auto_checkpoint_interval
        self.prev_checkpoint_hash: Optional[str] = None

    def register_company(
        self,
        company_name: str,
        founding_capital_usd: float,
        industry_sector: IndustrySector,
        sovereign_signature: str,
        is_ai: bool = False
    ) -> Company:
        """Register a new company (shell company creation)"""
        company_id = str(uuid.uuid4())

        company = Company(
            company_id=company_id,
            company_name=company_name,
            founding_capital_usd=founding_capital_usd,
            industry_sector=industry_sector,
            sovereign_signature=sovereign_signature,
            is_ai=is_ai
        )

        self.companies[company_id] = company
        return company

    def execute_operation(
        self,
        company_id: str,
        operation_type: OperationType,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a business operation for a company.
        Returns resource delta and decision trace.
        """
        if company_id not in self.companies:
            raise ValueError(f"Company {company_id} not found")

        company = self.companies[company_id]
        decision_trace = []
        resource_delta = {
            "employees": 0,
            "cash_usd": 0.0,
            "inventory_units": 0,
            "market_share_pct": 0.0,
            "brand_value": 0.0
        }

        # Execute based on operation type
        if operation_type == OperationType.HIRE:
            num_employees = params.get("num_employees", 1)
            cost = num_employees * self.market_conditions.labor_cost_per_employee_usd

            if company.resources.cash_usd >= cost:
                company.resources.employees += num_employees
                company.resources.cash_usd -= cost
                resource_delta["employees"] = num_employees
                resource_delta["cash_usd"] = -cost

                # Record transaction
                company.ledger.record_transaction(
                    tick=self.current_tick,
                    from_company_id=company_id,
                    to_company_id=None,
                    amount_usd=cost,
                    transaction_type=TransactionType.EXPENSE,
                    debit_account=Account.OPERATING_EXPENSES,
                    credit_account=Account.CASH,
                    metadata={"description": f"Hired {num_employees} employees"}
                )

                decision_trace.append({"step": "check_cash", "result": "PASS"})
                decision_trace.append({"step": "hire_employees", "result": "SUCCESS", "details": {"count": num_employees}})
            else:
                decision_trace.append({"step": "check_cash", "result": "FAIL", "details": {"required": cost, "available": company.resources.cash_usd}})

        elif operation_type == OperationType.PRODUCE:
            units = params.get("units", 10)
            min_employees = units // 10  # Productivity: 10 units per employee

            if company.resources.employees >= min_employees:
                material_cost = units * self.market_conditions.raw_material_cost_usd

                if company.resources.cash_usd >= material_cost:
                    company.resources.inventory_units += units
                    company.resources.cash_usd -= material_cost
                    resource_delta["inventory_units"] = units
                    resource_delta["cash_usd"] = -material_cost

                    # Record transaction
                    company.ledger.record_transaction(
                        tick=self.current_tick,
                        from_company_id=company_id,
                        to_company_id=None,
                        amount_usd=material_cost,
                        transaction_type=TransactionType.EXPENSE,
                        debit_account=Account.COGS,
                        credit_account=Account.CASH,
                        metadata={"description": f"Produced {units} units"}
                    )

                    decision_trace.append({"step": "check_employees", "result": "PASS"})
                    decision_trace.append({"step": "produce_goods", "result": "SUCCESS", "details": {"units": units}})
                else:
                    decision_trace.append({"step": "check_cash", "result": "FAIL"})
            else:
                decision_trace.append({"step": "check_employees", "result": "FAIL", "details": {"required": min_employees, "available": company.resources.employees}})

        elif operation_type == OperationType.MARKET:
            # Sell inventory to market
            units_to_sell = min(company.resources.inventory_units, params.get("units", company.resources.inventory_units))

            if units_to_sell > 0:
                # Revenue depends on demand multiplier
                base_price = 150.0  # Base price per unit
                revenue = units_to_sell * base_price * self.market_conditions.demand_multiplier

                company.resources.inventory_units -= units_to_sell
                company.resources.cash_usd += revenue
                company.financial.current_tick_revenue += revenue
                company.financial.total_revenue_usd += revenue
                company.metrics.market_share_pct += 0.1 * units_to_sell  # Incremental market share gain

                resource_delta["inventory_units"] = -units_to_sell
                resource_delta["cash_usd"] = revenue
                resource_delta["market_share_pct"] = 0.1 * units_to_sell

                # Record transaction
                company.ledger.record_transaction(
                    tick=self.current_tick,
                    from_company_id=None,  # External market
                    to_company_id=company_id,
                    amount_usd=revenue,
                    transaction_type=TransactionType.REVENUE,
                    debit_account=Account.CASH,
                    credit_account=Account.REVENUE,
                    metadata={"description": f"Sold {units_to_sell} units to market"}
                )

                decision_trace.append({"step": "sell_to_market", "result": "SUCCESS", "details": {"units": units_to_sell, "revenue": revenue}})
            else:
                decision_trace.append({"step": "check_inventory", "result": "FAIL", "details": {"available": 0}})

        elif operation_type == OperationType.R_AND_D:
            # Research & Development investment
            investment = params.get("amount_usd", 10000.0)

            if company.resources.cash_usd >= investment:
                company.resources.cash_usd -= investment
                company.metrics.brand_value += investment * 0.05  # R&D increases brand value
                resource_delta["cash_usd"] = -investment
                resource_delta["brand_value"] = investment * 0.05

                # Record transaction
                company.ledger.record_transaction(
                    tick=self.current_tick,
                    from_company_id=company_id,
                    to_company_id=None,
                    amount_usd=investment,
                    transaction_type=TransactionType.EXPENSE,
                    debit_account=Account.OPERATING_EXPENSES,
                    credit_account=Account.CASH,
                    metadata={"description": "R&D investment"}
                )

                decision_trace.append({"step": "invest_r_and_d", "result": "SUCCESS", "details": {"investment": investment}})
            else:
                decision_trace.append({"step": "check_cash", "result": "FAIL"})

        # Update tick trackers
        company.current_tick = self.current_tick

        return {
            "operation_id": str(uuid.uuid4()),
            "company_id": company_id,
            "tick": self.current_tick,
            "operation_type": operation_type.value,
            "resource_delta": resource_delta,
            "decision_trace": decision_trace
        }

    def tick(self):
        """Advance simulation by one tick (deterministic)"""
        self.current_tick += 1

        # Reset per-tick financials
        for company in self.companies.values():
            company.financial.current_tick_revenue = 0.0
            company.financial.current_tick_expenses = 0.0

        # Update market conditions (deterministic fluctuation)
        self._update_market_conditions()

        # Pay employee salaries (automatic expense)
        for company in self.companies.values():
            if company.resources.employees > 0:
                salary_cost = company.resources.employees * self.market_conditions.labor_cost_per_employee_usd
                company.resources.cash_usd -= salary_cost
                company.financial.current_tick_expenses += salary_cost
                company.financial.total_expenses_usd += salary_cost

                # Record transaction
                company.ledger.record_transaction(
                    tick=self.current_tick,
                    from_company_id=company.company_id,
                    to_company_id=None,
                    amount_usd=salary_cost,
                    transaction_type=TransactionType.EXPENSE,
                    debit_account=Account.OPERATING_EXPENSES,
                    credit_account=Account.CASH,
                    metadata={"description": f"Salaries for {company.resources.employees} employees"}
                )

        # Update company states
        for company in self.companies.values():
            company.prev_state_hash = company.compute_state_hash()
            company.current_tick = self.current_tick

    def _update_market_conditions(self):
        """Update market conditions deterministically (based on seed)"""
        # Small random fluctuations (deterministic via seed)
        self.market_conditions.demand_multiplier += random.uniform(-0.05, 0.05)
        self.market_conditions.demand_multiplier = max(0.5, min(2.0, self.market_conditions.demand_multiplier))

        self.market_conditions.interest_rate_pct += random.uniform(-0.2, 0.2)
        self.market_conditions.interest_rate_pct = max(0, min(15, self.market_conditions.interest_rate_pct))

    def get_market_state(self) -> Dict[str, Any]:
        """Get current market state with company rankings"""
        # Rank companies by revenue
        ranked = sorted(
            self.companies.values(),
            key=lambda c: c.financial.total_revenue_usd,
            reverse=True
        )

        rankings = []
        for rank, company in enumerate(ranked, 1):
            rankings.append({
                "company_id": company.company_id,
                "company_name": company.company_name,
                "revenue_usd": company.financial.total_revenue_usd,
                "market_share_pct": company.metrics.market_share_pct,
                "rank": rank,
                "employees": company.resources.employees,
                "is_ai": company.is_ai
            })

        market_state = {
            "tick": self.current_tick,
            "market_conditions": self.market_conditions.to_dict(),
            "company_rankings": rankings,
            "prev_state_hash": self.prev_market_hash
        }

        # Compute Merkle state hash
        canonical_json = json.dumps(market_state, sort_keys=True, separators=(',', ':'))
        market_state["merkle_state_hash"] = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

        # Update history
        self.prev_market_hash = market_state["merkle_state_hash"]
        self.market_state_history.append(market_state)

        return market_state

    def get_company(self, company_id: str) -> Optional[Company]:
        """Retrieve company by ID"""
        return self.companies.get(company_id)

    def verify_all_chains(self) -> Dict[str, bool]:
        """Verify Merkle chain integrity for all companies"""
        results = {}
        for company_id, company in self.companies.items():
            results[company_id] = company.ledger.verify_chain()
        return results
    
    def create_checkpoint(self, checkpoint_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a checkpoint of the current game state.
        Optionally pin to IPFS if ipfs_bridge is configured.
        
        Args:
            checkpoint_id: Optional UUID for checkpoint, generated if not provided
        
        Returns:
            Checkpoint capsule dictionary
        """
        checkpoint_id = checkpoint_id or str(uuid.uuid4())
        timestamp_utc = datetime.now(timezone.utc).isoformat()
        
        # Build flow state snapshot
        flow_state = {
            "companies": {cid: c.to_dict() for cid, c in self.companies.items()},
            "market_conditions": self.market_conditions.to_dict(),
            "total_companies": len(self.companies),
            "seed": self.seed
        }
        
        # Compute canonical hash
        canonical_json = json.dumps(flow_state, sort_keys=True, separators=(',', ':'))
        canonical_sha256 = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
        
        # Compute Merkle root from all company ledger chains
        company_hashes = [c.ledger.get_chain_head_hash() for c in self.companies.values()]
        if company_hashes:
            combined = ''.join(sorted(company_hashes))
            merkle_root = hashlib.sha256(combined.encode('utf-8')).hexdigest()
        else:
            merkle_root = canonical_sha256  # Fallback if no companies
        
        # Build resume token
        resume_token = f"{checkpoint_id}@{self.current_tick}"
        
        # Build checkpoint capsule
        checkpoint = {
            "checkpoint_id": checkpoint_id,
            "tick": self.current_tick,
            "timestamp_utc": timestamp_utc,
            "flow_state": flow_state,
            "resume_token": resume_token,
            "canonical_sha256": canonical_sha256,
            "prev_checkpoint_hash": self.prev_checkpoint_hash,
            "merkle_root": merkle_root,
            "replay_authorized": True,
            "metadata": {
                "creator": "game_engine",
                "purpose": "auto_checkpoint" if self.auto_checkpoint_interval else "manual_save"
            }
        }
        
        # Pin to IPFS if bridge is available
        if self.ipfs_bridge and self.ipfs_bridge.is_available():
            try:
                # Generate multihash
                multihash = self.ipfs_bridge.generate_multihash(flow_state)
                
                # Pin capsule to IPFS
                ipfs_cid = self.ipfs_bridge.pin_capsule(checkpoint, codec="dag-json")
                
                if ipfs_cid:
                    checkpoint["ipfs_cid"] = ipfs_cid
                    checkpoint["multihash"] = multihash
                    checkpoint["codec"] = "dag-json"
                    checkpoint["storage_uri"] = f"ipfs://{ipfs_cid}"
            except Exception as e:
                print(f"Warning: IPFS pinning failed: {e}")
                # Continue without IPFS fields (graceful degradation)
        
        # Update checkpoint history
        self.prev_checkpoint_hash = canonical_sha256
        self.checkpoint_history.append(checkpoint)
        
        return checkpoint
    
    def load_checkpoint(self, cid: str) -> None:
        """
        Load a checkpoint from IPFS by CID and restore game state.
        
        Args:
            cid: CIDv1 identifier of the checkpoint
        
        Raises:
            ValueError: If IPFS bridge not configured or checkpoint invalid
        """
        if not self.ipfs_bridge:
            raise ValueError("IPFS bridge not configured")
        
        # Fetch checkpoint from IPFS
        checkpoint = self.ipfs_bridge.fetch_capsule(cid)
        if not checkpoint:
            raise ValueError(f"Failed to fetch checkpoint with CID: {cid}")
        
        # Verify CID matches payload
        if not self.ipfs_bridge.verify_cid(cid, checkpoint):
            raise ValueError(f"CID verification failed for: {cid}")
        
        # Verify canonical hash
        flow_state = checkpoint.get("flow_state")
        if not flow_state:
            raise ValueError("Invalid checkpoint: missing flow_state")
        
        canonical_json = json.dumps(flow_state, sort_keys=True, separators=(',', ':'))
        computed_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
        
        if computed_hash != checkpoint.get("canonical_sha256"):
            raise ValueError("Canonical hash verification failed")
        
        # Restore game state
        self.current_tick = checkpoint["tick"]
        self.seed = flow_state["seed"]
        random.seed(self.seed)  # Re-initialize RNG for deterministic replay
        
        # Restore market conditions
        market_data = flow_state["market_conditions"]
        self.market_conditions = MarketConditions(**market_data)
        
        # Restore companies
        self.companies.clear()
        for company_id, company_data in flow_state["companies"].items():
            # Reconstruct company from state snapshot
            company = Company(
                company_id=company_id,
                company_name=company_data["company_name"],
                founding_capital_usd=0.0,  # Will be overridden
                industry_sector=IndustrySector.TECH,  # Placeholder, will be restored
                sovereign_signature="restored",
                is_ai=company_data.get("is_ai", False)
            )
            
            # Restore resources
            company.resources = CompanyResources(**company_data["resources"])
            company.financial = FinancialState(**company_data["financial_state"])
            company.metrics = PerformanceMetrics(**company_data["performance_metrics"])
            company.current_tick = company_data["tick"]
            company.prev_state_hash = company_data.get("prev_state_hash")
            
            self.companies[company_id] = company
        
        # Update checkpoint tracking
        self.prev_checkpoint_hash = checkpoint["canonical_sha256"]
        
        print(f"✅ Checkpoint restored from CID: {cid} (tick {self.current_tick})")
    
    def verify_checkpoint_chain(self, checkpoint_ids: List[str]) -> bool:
        """
        Verify Merkle lineage for a sequence of checkpoints.
        
        Args:
            checkpoint_ids: List of checkpoint IDs in chronological order
        
        Returns:
            True if all checkpoints form a valid chain, False otherwise
        """
        if not self.ipfs_bridge:
            # Fallback: verify from local checkpoint history
            for i, checkpoint_id in enumerate(checkpoint_ids):
                checkpoint = next((c for c in self.checkpoint_history if c["checkpoint_id"] == checkpoint_id), None)
                if not checkpoint:
                    return False
                
                if i > 0:
                    prev_checkpoint = next((c for c in self.checkpoint_history if c["checkpoint_id"] == checkpoint_ids[i-1]), None)
                    if not prev_checkpoint:
                        return False
                    
                    if checkpoint.get("prev_checkpoint_hash") != prev_checkpoint.get("canonical_sha256"):
                        return False
            
            return True
        
        # IPFS-backed verification
        prev_hash = None
        for checkpoint_id in checkpoint_ids:
            # Find checkpoint (either in history or fetch by ID)
            checkpoint = next((c for c in self.checkpoint_history if c["checkpoint_id"] == checkpoint_id), None)
            
            if not checkpoint:
                return False
            
            # Verify CID if present
            if "ipfs_cid" in checkpoint:
                if not self.ipfs_bridge.verify_cid(checkpoint["ipfs_cid"], checkpoint):
                    return False
            
            # Verify chain link
            if prev_hash is not None:
                if checkpoint.get("prev_checkpoint_hash") != prev_hash:
                    return False
            
            prev_hash = checkpoint["canonical_sha256"]
        
        return True
