"""
AI Agent Orchestrator - manages multiple AI competitors.
Spawns and runs AI companies in the game simulation.
"""

from typing import Dict, List, Any
import hashlib

from game_engine import GameEngine, IndustrySector
from ai_agents.rule_based_agent import RuleBasedAgent, AgentStrategy


class AgentOrchestrator:
    """
    Manages multiple AI competitors.
    Spawns AI companies and executes their decisions each tick.
    """

    def __init__(self, game_engine: GameEngine):
        self.game = game_engine
        self.agents: Dict[str, RuleBasedAgent] = {}  # company_id -> agent

    def spawn_ai_companies(
        self,
        num_companies: int = 3,
        starting_capital: float = 100000.0
    ):
        """Spawn AI-controlled companies with different strategies"""

        strategies = [AgentStrategy.AGGRESSIVE_GROWTH, AgentStrategy.CONSERVATIVE, AgentStrategy.BALANCED]
        sectors = [IndustrySector.TECH, IndustrySector.MANUFACTURING, IndustrySector.SERVICES]

        for i in range(num_companies):
            # Generate deterministic sovereign signature for AI
            signature_input = f"AI_COMPANY_{i}_{self.game.seed}"
            sovereign_sig = hashlib.sha256(signature_input.encode()).hexdigest()

            # Register AI company
            company = self.game.register_company(
                company_name=f"AI Corp {i+1}",
                founding_capital_usd=starting_capital,
                industry_sector=sectors[i % len(sectors)],
                sovereign_signature=sovereign_sig,
                is_ai=True
            )

            # Create agent with strategy
            agent = RuleBasedAgent(company, strategy=strategies[i % len(strategies)])
            self.agents[company.company_id] = agent

            print(f"✓ Spawned AI company: {company.company_name} (strategy: {agent.strategy.value})")

    def run_all_agents(self, tick: int):
        """Execute all AI agents' decisions for current tick"""
        for company_id, agent in self.agents.items():
            # Get decision from agent
            decision = agent.decide_next_operation(
                market_conditions=self.game.market_conditions,
                tick=tick
            )

            # Execute operation if decision made
            if decision:
                try:
                    self.game.execute_operation(
                        company_id=company_id,
                        operation_type=decision["operation_type"],
                        params=decision["params"]
                    )
                except Exception as e:
                    print(f"⚠️  AI agent {agent.company.company_name} decision failed: {e}")

    def get_agent_performance(self) -> List[Dict]:
        """Get performance metrics for all AI agents"""
        performance = []

        for company_id, agent in self.agents.items():
            company = agent.company
            performance.append({
                "company_id": company_id,
                "company_name": company.company_name,
                "strategy": agent.strategy.value,
                "revenue": company.financial.total_revenue_usd,
                "cash": company.resources.cash_usd,
                "employees": company.resources.employees,
                "market_share": company.metrics.market_share_pct,
                "decisions_made": len(agent.decision_history)
            })

        return performance

    def export_all_decision_traces(self) -> Dict[str, Any]:
        """Export decision history for all agents (for audit)"""
        return {
            company_id: agent.get_decision_summary()
            for company_id, agent in self.agents.items()
        }
