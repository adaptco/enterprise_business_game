"""
Enterprise Business Game - Demonstration Script
Showcases full game loop with AI competitors and SSOT integration.
"""

import sys
import time
sys.path.append('./src')

from game_engine import GameEngine, IndustrySector, OperationType
from ai_agents import AgentOrchestrator
from ssot_bridge import SSOTBridge


def print_banner():
    """Print game banner"""
    print("\n" + "="*60)
    print("🏙️  ENTERPRISE BUSINESS GAME DEMO")
    print("    Shell Companies • AI Competitors • Merkle Audit Trails")
    print("="*60 + "\n")


def print_market_state(game: GameEngine):
    """Display current market state"""
    market = game.get_market_state()

    print(f"\n📊 MARKET STATE (Tick {market['tick']})")
    print("-" * 60)
    conditions = market['market_conditions']
    print(f"  Demand Multiplier: {conditions['demand_multiplier']:.2f}x")
    print(f"  Interest Rate: {conditions['interest_rate_pct']:.1f}%")
    print(f"  Labor Cost: ${conditions['labor_cost_per_employee_usd']:,.0f}/employee")
    print(f"  Raw Materials: ${conditions['raw_material_cost_usd']:.0f}/unit")
    print()


def print_leaderboard(game: GameEngine):
    """Display company rankings"""
    market = game.get_market_state()
    rankings = market['company_rankings']

    print("🏆 LEADERBOARD")
    print("-" * 60)
    print(f"{'Rank':<6} {'Company':<20} {'Revenue':<15} {'Employees':<10} {'Type'}")
    print("-" * 60)

    for company in rankings:
        rank = company['rank']
        name = company['company_name'][:19]
        revenue = f"${company['revenue_usd']:,.0f}"
        employees = company['employees']
        ctype = "AI" if company['is_ai'] else "Player"

        print(f"{rank:<6} {name:<20} {revenue:<15} {employees:<10} {ctype}")

    print()


def print_company_details(company):
    """Display detailed company state"""
    print(f"\n🏢 {company.company_name.upper()}")
    print("-" * 60)
    print(f"  ID: {company.company_id}")
    print(f"  Industry: {company.industry_sector.value}")
    print(f"  Is AI: {company.is_ai}")
    print()
    print(f"  💰 Cash: ${company.resources.cash_usd:,.2f}")
    print(f"  👥 Employees: {company.resources.employees}")
    print(f"  📦 Inventory: {company.resources.inventory_units} units")
    print()
    print(f"  💵 Total Revenue: ${company.financial.total_revenue_usd:,.2f}")
    print(f"  💸 Total Expenses: ${company.financial.total_expenses_usd:,.2f}")
    print(f"  📈 Net Income: ${company.financial.net_income_usd:,.2f}")
    print(f"  📊 Market Share: {company.metrics.market_share_pct:.2f}%")
    print()


def run_demo():
    """Run full demonstration"""
    print_banner()

    # Initialize game engine
    print("🎮 Initializing game engine...")
    game = GameEngine(seed=42)
    print("✓ Game engine ready\n")

    # Register player company
    print("🏗️  Registering player company...")
    player_company = game.register_company(
        company_name="Player Corp",
        founding_capital_usd=100000.0,
        industry_sector=IndustrySector.TECH,
        sovereign_signature="a" * 64,  # Mock signature
        is_ai=False
    )
    print(f"✓ Registered: {player_company.company_name}")
    print(f"  Genesis Hash: {player_company.merkle_genesis_hash[:16]}...")
    print()

    # Spawn AI competitors
    print("🤖 Spawning AI competitors...")
    orchestrator = AgentOrchestrator(game)
    orchestrator.spawn_ai_companies(num_companies=3, starting_capital=100000.0)
    print()

    # Initialize SSOT bridge (will fail gracefully if SSOT API not running)
    print("🔗 Connecting to SSOT API...")
    ssot = SSOTBridge()
    ssot_enabled = ssot.get_latest_hash() is not None
    if ssot_enabled:
        print("✓ SSOT integration active\n")
    else:
        print("⚠️  SSOT API not available (run ssot-integration/src/ssot_api_ingest.py first)")
        print("   Continuing without SSOT integration...\n")

    # Display initial state
    print_market_state(game)
    print_company_details(player_company)

    # Simulate game loop
    print("\n🎬 Starting simulation (10 ticks)...")
    print("="*60)

    for i in range(10):
        print(f"\n⏱️  Tick {i+1}/10")

        # Player operations (simple strategy)
        if i % 2 == 0:  # Every other tick
            if player_company.resources.cash_usd > 20000 and player_company.resources.employees < 5:
                print("  🧑 Player: Hiring employees...")
                game.execute_operation(
                    player_company.company_id,
                    OperationType.HIRE,
                    {"num_employees": 2}
                )

        if player_company.resources.employees > 0:
            print("  🏭 Player: Producing goods...")
            game.execute_operation(
                player_company.company_id,
                OperationType.PRODUCE,
                {"units": player_company.resources.employees * 10}
            )

        if player_company.resources.inventory_units > 20:
            print("  💼 Player: Selling to market...")
            game.execute_operation(
                player_company.company_id,
                OperationType.MARKET,
                {"units": player_company.resources.inventory_units}
            )

        # AI agent decisions
        print("  🤖 AI agents making decisions...")
        orchestrator.run_all_agents(tick=game.current_tick)

        # Advance tick
        game.tick()

        # Emit to SSOT (if enabled)
        if ssot_enabled and i % 3 == 0:  # Every 3 ticks
            market_state = game.get_market_state()
            company_snapshots = [c.to_dict() for c in game.companies.values()]
            ssot.emit_game_state_capsule(
                tick=game.current_tick,
                market_state=market_state,
                company_snapshots=company_snapshots
            )

        time.sleep(0.3)  # Slight delay for readability

    # Final results
    print("\n" + "="*60)
    print("📋 FINAL RESULTS")
    print("="*60)

    print_market_state(game)
    print_leaderboard(game)

    # Verify Merkle chains
    print("🔐 MERKLE CHAIN VERIFICATION")
    print("-" * 60)
    results = game.verify_all_chains()
    for company_id, valid in results.items():
        company = game.get_company(company_id)
        status = "✓ INTACT" if valid else "✗ CORRUPTED"
        print(f"  {company.company_name}: {status}")
    print()

    # AI performance
    print("🤖 AI AGENT PERFORMANCE")
    print("-" * 60)
    for perf in orchestrator.get_agent_performance():
        print(f"  {perf['company_name']} ({perf['strategy']})")
        print(f"     Revenue: ${perf['revenue']:,.2f}, Cash: ${perf['cash']:,.2f}")
        print(f"     Decisions Made: {perf['decisions_made']}")
    print()

    # SSOT lineage verification
    if ssot_enabled:
        print("🔗 SSOT LINEAGE VERIFICATION")
        print("-" * 60)
        if ssot.verify_lineage():
            print("  ✓ Local hash matches SSOT API")
            print(f"  Hash: {ssot.last_capsule_hash[:16] if ssot.last_capsule_hash else 'None'}...")
        else:
            print("  ✗ Hash mismatch detected!")
        print()

    print("✅ Demo complete!\n")


if __name__ == "__main__":
    try:
        run_demo()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo failed: {e}")
        raise
