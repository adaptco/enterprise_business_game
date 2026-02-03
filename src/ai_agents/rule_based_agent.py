"""
Rule-based AI agent for autonomous business decisions.
Implements deterministic decision trees for competing in the market.
"""

from typing import Dict, Any, Optional
from enum import Enum
import random

from game_engine import Company, MarketConditions, OperationType


class AgentStrategy(Enum):
    """AI agent strategy profiles"""
    AGGRESSIVE_GROWTH = "AGGRESSIVE_GROWTH"  # High risk, expand fast
    CONSERVATIVE = "CONSERVATIVE"  # Low risk, slow growth
    BALANCED = "BALANCED"  # Moderate risk/reward


class RuleBasedAgent:
    """
    Deterministic AI competitor using decision tree logic.
    All decisions are logged with rationale for audit trail.
    """

    def __init__(self, company: Company, strategy: AgentStrategy = AgentStrategy.BALANCED):
        self.company = company
        self.strategy = strategy
        self.decision_history: list[Dict[str, Any]] = []

    def decide_next_operation(
        self,
        market_conditions: MarketConditions,
        tick: int
    ) -> Optional[Dict[str, Any]]:
        """
        Decide next business operation based on company state and market.
        Returns operation type and parameters, or None if no action.
        """
        decision_trace = {"tick": tick, "strategy": self.strategy.value}

        # Decision tree based on strategy
        if self.strategy == AgentStrategy.AGGRESSIVE_GROWTH:
            decision = self._aggressive_strategy(market_conditions, decision_trace)
        elif self.strategy == AgentStrategy.CONSERVATIVE:
            decision = self._conservative_strategy(market_conditions, decision_trace)
        else:  # BALANCED
            decision = self._balanced_strategy(market_conditions, decision_trace)

        if decision:
            decision["decision_trace"] = decision_trace
            self.decision_history.append(decision)

        return decision

    def _aggressive_strategy(
        self,
        market: MarketConditions,
        trace: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """High-risk, high-reward strategy"""

        # Priority 1: Expand if market is hot
        if market.demand_multiplier > 1.2:
            trace["condition"] = "high_demand"
            trace["decision"] = "hire_and_produce"

            # Hire employees aggressively
            if self.company.resources.cash_usd > 50000:
                return {
                    "operation_type": OperationType.HIRE,
                    "params": {"num_employees": 5}
                }

        # Priority 2: Produce and sell if we have employees
        if self.company.resources.employees >= 3:
            trace["condition"] = "has_employees"
            trace["decision"] = "produce"

            return {
                "operation_type": OperationType.PRODUCE,
                "params": {"units": self.company.resources.employees * 10}
            }

        # Priority 3: Sell inventory
        if self.company.resources.inventory_units > 20:
            trace["condition"] = "high_inventory"
            trace["decision"] = "market"

            return {
                "operation_type": OperationType.MARKET,
                "params": {"units": self.company.resources.inventory_units}
            }

        # Priority 4: Hire if cash available
        if self.company.resources.cash_usd > 30000:
            trace["condition"] = "cash_available"
            trace["decision"] = "hire"

            return {
                "operation_type": OperationType.HIRE,
                "params": {"num_employees": 2}
            }

        return None

    def _conservative_strategy(
        self,
        market: MarketConditions,
        trace: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Low-risk, sustainable growth strategy"""

        # Priority 1: Sell inventory first (cash flow)
        if self.company.resources.inventory_units > 10:
            trace["condition"] = "has_inventory"
            trace["decision"] = "market"

            return {
                "operation_type": OperationType.MARKET,
                "params": {"units": min(self.company.resources.inventory_units, 20)}
            }

        # Priority 2: Produce only if profitable
        if self.company.resources.employees > 0 and market.demand_multiplier > 0.9:
            trace["condition"] = "profitable_to_produce"
            trace["decision"] = "produce"

            units = min(self.company.resources.employees * 10, 50)
            return {
                "operation_type": OperationType.PRODUCE,
                "params": {"units": units}
            }

        # Priority 3: Hire only if very profitable
        if self.company.resources.cash_usd > 100000 and self.company.financial.total_revenue_usd > 50000:
            trace["condition"] = "high_profit"
            trace["decision"] = "hire"

            return {
                "operation_type": OperationType.HIRE,
                "params": {"num_employees": 1}
            }

        # Priority 4: R&D if cash is safe
        if self.company.resources.cash_usd > 80000:
            trace["condition"] = "cash_safe"
            trace["decision"] = "r_and_d"

            return {
                "operation_type": OperationType.R_AND_D,
                "params": {"amount_usd": 10000}
            }

        return None

    def _balanced_strategy(
        self,
        market: MarketConditions,
        trace: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Moderate risk/reward strategy"""

        # Priority 1: Sell if inventory is building up
        if self.company.resources.inventory_units > 30:
            trace["condition"] = "inventory_buildup"
            trace["decision"] = "market"

            return {
                "operation_type": OperationType.MARKET,
                "params": {"units": self.company.resources.inventory_units // 2}
            }

        # Priority 2: Produce if we have capacity
        if self.company.resources.employees >= 2:
            trace["condition"] = "has_capacity"
            trace["decision"] = "produce"

            units = self.company.resources.employees * 10
            return {
                "operation_type": OperationType.PRODUCE,
                "params": {"units": units}
            }

        # Priority 3: Hire if cash allows and market is decent
        if self.company.resources.cash_usd > 60000 and market.demand_multiplier > 0.8:
            trace["condition"] = "growth_opportunity"
            trace["decision"] = "hire"

            return {
                "operation_type": OperationType.HIRE,
                "params": {"num_employees": 2}
            }

        # Priority 4: R&D for brand building
        if self.company.resources.cash_usd > 50000 and self.company.metrics.brand_value < 1000:
            trace["condition"] = "low_brand"
            trace["decision"] = "r_and_d"

            return {
                "operation_type": OperationType.R_AND_D,
                "params": {"amount_usd": 5000}
            }

        return None

    def get_decision_summary(self) -> Dict[str, Any]:
        """Export decision history for analysis"""
        return {
            "company_id": self.company.company_id,
            "company_name": self.company.company_name,
            "strategy": self.strategy.value,
            "total_decisions": len(self.decision_history),
            "decisions": self.decision_history
        }
