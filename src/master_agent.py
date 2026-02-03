"""
Master Agent - Self-Running, Self-Tuning Orchestrator
Autonomous game loop with health monitoring and SSOT integration.
"""

import os
import sys
import time
import logging
import requests
from typing import Optional

sys.path.append('./src')

from game_engine import GameEngine, IndustrySector, OperationType
from ai_agents import AgentOrchestrator
from ssot_bridge import SSOTBridge

# Configuration from environment
GAME_API_URL = os.getenv("GAME_API_URL", "http://localhost:8001")
SSOT_API_URL = os.getenv("SSOT_API_URL", "http://localhost:8000")
TICK_INTERVAL_SECONDS = int(os.getenv("TICK_INTERVAL_SECONDS", "5"))
AUTO_SPAWN_AI = os.getenv("AUTO_SPAWN_AI", "true").lower() == "true"
NUM_AI_COMPANIES = int(os.getenv("NUM_AI_COMPANIES", "3"))

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MasterAgent")


class MasterAgent:
    """
    Self-running, self-tuning, self-healing orchestrator.
    Controls the game loop and maintains system health.
    """

    def __init__(self):
        self.game = GameEngine(seed=42)
        self.orchestrator = AgentOrchestrator(self.game)
        self.ssot = SSOTBridge(ssot_api_url=SSOT_API_URL)
        self.running = True
        self.tick_count = 0

        # Health thresholds
        self.min_cash_threshold = 10000
        self.bankruptcy_count = 0

    def initialize(self):
        """Initialize game state"""
        logger.info("🎮 Master Agent initializing...")

        # Spawn AI companies if configured
        if AUTO_SPAWN_AI:
            logger.info(f"🤖 Spawning {NUM_AI_COMPANIES} AI companies...")
            self.orchestrator.spawn_ai_companies(
                num_companies=NUM_AI_COMPANIES,
                starting_capital=100000.0
            )
            logger.info(f"✓ {NUM_AI_COMPANIES} AI companies spawned")

        # Verify SSOT connection
        try:
            latest_hash = self.ssot.get_latest_hash()
            logger.info(f"🔗 SSOT API connected (latest hash: {latest_hash[:16] if latest_hash else 'genesis'}...)")
        except Exception as e:
            logger.warning(f"⚠️  SSOT API not available: {e}")

        logger.info("✓ Master Agent ready")

    def tick(self):
        """Execute one game tick"""
        self.tick_count += 1
        logger.info(f"\n⏱️  Tick {self.tick_count}")

        # Run AI agents
        logger.debug("🤖 AI agents making decisions...")
        self.orchestrator.run_all_agents(tick=self.game.current_tick)

        # Advance game state
        self.game.tick()

        # Get market state
        market_state = self.game.get_market_state()
        logger.info(f"📊 Market: Demand {market_state['market_conditions']['demand_multiplier']:.2f}x, "
                   f"Companies: {len(market_state['company_rankings'])}")

        # Emit to SSOT every 3 ticks
        if self.tick_count % 3 == 0:
            self._emit_to_ssot(market_state)

        # Health monitoring
        self._monitor_health()

        # Self-tuning
        if self.tick_count % 10 == 0:
            self._tune_market()

    def _emit_to_ssot(self, market_state):
        """Emit game state to SSOT API"""
        try:
            company_snapshots = [c.to_dict() for c in self.game.companies.values()]
            self.ssot.emit_game_state_capsule(
                tick=self.game.current_tick,
                market_state=market_state,
                company_snapshots=company_snapshots
            )
            logger.debug("✓ Emitted state capsule to SSOT")
        except Exception as e:
            logger.warning(f"⚠️  Failed to emit to SSOT: {e}")

    def _monitor_health(self):
        """Monitor game health and detect anomalies"""
        # Count bankrupt companies
        bankrupt_companies = [
            c for c in self.game.companies.values()
            if c.resources.cash_usd < 0 and c.resources.employees > 0
        ]

        if bankrupt_companies:
            logger.warning(f"⚠️  {len(bankrupt_companies)} companies bankrupt but still operating")
            for company in bankrupt_companies:
                logger.warning(f"   {company.company_name}: Cash ${company.resources.cash_usd:,.0f}, "
                              f"Employees {company.resources.employees}")
            self.bankruptcy_count += len(bankrupt_companies)

        # Verify Merkle chains periodically
        if self.tick_count % 20 == 0:
            results = self.game.verify_all_chains()
            if not all(results.values()):
                logger.error("❌ MERKLE CHAIN CORRUPTION DETECTED!")
                for company_id, valid in results.items():
                    if not valid:
                        company = self.game.get_company(company_id)
                        logger.error(f"   {company.company_name}: Chain broken")
                # In production, this would trigger governance review
            else:
                logger.info("✓ All Merkle chains intact")

    def _tune_market(self):
        """Self-tuning: adjust market conditions based on game health"""
        # Calculate average company health
        if not self.game.companies:
            return

        avg_cash = sum(c.resources.cash_usd for c in self.game.companies.values()) / len(self.game.companies)
        avg_revenue = sum(c.financial.total_revenue_usd for c in self.game.companies.values()) / len(self.game.companies)

        logger.info(f"🔧 Tuning check: Avg Cash ${avg_cash:,.0f}, Avg Revenue ${avg_revenue:,.0f}")

        # If economy is struggling, stimulate demand
        if avg_cash < self.min_cash_threshold:
            old_demand = self.game.market_conditions.demand_multiplier
            self.game.market_conditions.demand_multiplier = min(2.0, old_demand * 1.1)
            logger.info(f"   📈 Stimulating economy: Demand {old_demand:.2f}x → "
                       f"{self.game.market_conditions.demand_multiplier:.2f}x")

        # If economy is overheating, cool down
        if avg_cash > 200000 and avg_revenue > 100000:
            old_demand = self.game.market_conditions.demand_multiplier
            self.game.market_conditions.demand_multiplier = max(0.5, old_demand * 0.95)
            logger.info(f"   📉 Cooling economy: Demand {old_demand:.2f}x → "
                       f"{self.game.market_conditions.demand_multiplier:.2f}x")

    def run(self):
        """Main control loop"""
        self.initialize()

        logger.info(f"\n🚀 Starting game loop (tick interval: {TICK_INTERVAL_SECONDS}s)")
        logger.info("=" * 60)

        try:
            while self.running:
                self.tick()
                time.sleep(TICK_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            logger.info("\n⚠️  Master Agent shutting down (user interrupt)")
        except Exception as e:
            logger.error(f"\n❌ Master Agent failed: {e}", exc_info=True)
        finally:
            self._shutdown()

    def _shutdown(self):
        """Graceful shutdown"""
        logger.info("\n📊 FINAL STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Total ticks: {self.tick_count}")
        logger.info(f"Total companies: {len(self.game.companies)}")
        logger.info(f"Bankruptcy events: {self.bankruptcy_count}")

        # Final leaderboard
        market_state = self.game.get_market_state()
        logger.info("\n🏆 FINAL LEADERBOARD")
        for company in market_state['company_rankings'][:5]:
            logger.info(f"   {company['rank']}. {company['company_name']}: "
                       f"${company['revenue_usd']:,.0f} revenue")

        # Verify chains one last time
        results = self.game.verify_all_chains()
        if all(results.values()):
            logger.info("\n✓ All Merkle chains verified intact")
        else:
            logger.error("\n❌ Chain integrity failures detected")

        logger.info("\n✅ Master Agent shutdown complete")


if __name__ == "__main__":
    agent = MasterAgent()
    agent.run()
