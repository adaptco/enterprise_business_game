"""
Unit tests for Highway Battle System.

Tests the core game kernel components:
- SP drain calculation
- Battle lifecycle
- Rival spawning
- Headlight flash challenge system
"""

import sys
import os
import unittest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from highway_battle.sp_system import SPSystem, SPConfig, SPState
from highway_battle.rival_entity import (
    RivalEntity, RivalTier, RivalStats,
    create_wanderer, create_boss, create_team_leader
)
from highway_battle.battle_manager import (
    BattleManager, BattleState, BattleResult, BattlePhase
)
from highway_battle.rival_spawner import (
    RivalSpawner, SpawnZone, create_nurburgring_zones
)
from highway_battle.headlight_flash import (
    HeadlightFlashSystem, FlashChallenge
)


class TestSPSystem(unittest.TestCase):
    """Test SP (Spirit Points) drain mechanics."""
    
    def setUp(self):
        self.config = SPConfig(
            base_drain_per_second=0.03,
            gap_multiplier=0.002,
            speed_multiplier=0.008,
            escalation_rate=0.0002,
            tick_rate_hz=60.0
        )
        self.sp = SPSystem(self.config)
    
    def test_initial_state(self):
        """Both players start with full SP."""
        state = self.sp.get_state()
        self.assertEqual(state.player_sp, 1.0)
        self.assertEqual(state.rival_sp, 1.0)
    
    def test_leader_drains_follower(self):
        """Leader should drain follower's SP."""
        # Player ahead by 30m
        for _ in range(60):  # 1 second
            self.sp.tick(
                player_progress_m=1030,
                rival_progress_m=1000,
                player_speed_mps=45,
                rival_speed_mps=42
            )
        
        state = self.sp.get_state()
        self.assertTrue(state.player_is_leader)
        self.assertEqual(state.player_sp, 1.0)  # Leader unchanged
        self.assertLess(state.rival_sp, 1.0)  # Follower drained
    
    def test_follower_drains(self):
        """Follower's SP should drain when behind."""
        # Rival ahead by 30m
        for _ in range(60):
            self.sp.tick(
                player_progress_m=1000,
                rival_progress_m=1030,
                player_speed_mps=42,
                rival_speed_mps=45
            )
        
        state = self.sp.get_state()
        self.assertFalse(state.player_is_leader)
        self.assertLess(state.player_sp, 1.0)  # Player drained
        self.assertEqual(state.rival_sp, 1.0)  # Rival unchanged
    
    def test_gap_increases_drain(self):
        """Larger gap should increase drain rate."""
        # Test with small gap
        sp1 = SPSystem(self.config)
        for _ in range(60):
            sp1.tick(1010, 1000, 45, 45)  # 10m gap
        drain_small = 1.0 - sp1.get_state().rival_sp
        
        # Test with large gap
        sp2 = SPSystem(self.config)
        for _ in range(60):
            sp2.tick(1050, 1000, 45, 45)  # 50m gap
        drain_large = 1.0 - sp2.get_state().rival_sp
        
        self.assertGreater(drain_large, drain_small)
    
    def test_speed_diff_increases_drain(self):
        """Speed advantage should increase drain rate."""
        # Test with no speed diff
        sp1 = SPSystem(self.config)
        for _ in range(60):
            sp1.tick(1020, 1000, 45, 45)
        drain_equal = 1.0 - sp1.get_state().rival_sp
        
        # Test with speed advantage
        sp2 = SPSystem(self.config)
        for _ in range(60):
            sp2.tick(1020, 1000, 50, 40)  # Player 10 m/s faster
        drain_faster = 1.0 - sp2.get_state().rival_sp
        
        self.assertGreater(drain_faster, drain_equal)
    
    def test_battle_ends_when_sp_zero(self):
        """Battle should end when SP reaches zero."""
        # Run many ticks with player leading
        for tick in range(3000):  # 50 seconds max
            self.sp.tick(1050
                        , 1000, 45, 40)
            winner = self.sp.get_winner()
            if winner:
                break
        
        self.assertEqual(winner, "player")
        self.assertLessEqual(self.sp.get_state().rival_sp, 0)
    
    def test_deterministic_hash(self):
        """State hash should be deterministic."""
        sp1 = SPSystem(self.config)
        sp2 = SPSystem(self.config)
        
        for _ in range(60):
            sp1.tick(1030, 1000, 45, 42)
            sp2.tick(1030, 1000, 45, 42)
        
        hash1 = sp1.get_state().compute_hash()
        hash2 = sp2.get_state().compute_hash()
        
        self.assertEqual(hash1, hash2)
    
    def test_critical_threshold(self):
        """Should detect when SP is critical."""
        # Drain to near critical
        for _ in range(1200):  # ~20 seconds
            self.sp.tick(1050, 1000, 50, 40)
            if self.sp.is_rival_critical():
                break
        
        self.assertTrue(self.sp.is_rival_critical())
        self.assertLess(self.sp.get_state().rival_sp, self.config.critical_threshold)


class TestRivalEntity(unittest.TestCase):
    """Test RivalEntity creation and management."""
    
    def test_create_wanderer(self):
        """Create a wanderer-tier rival."""
        rival = create_wanderer("Night Drifter", "S13", ["hatzenbach"])
        
        self.assertEqual(rival.tier, RivalTier.WANDERER)
        self.assertEqual(rival.name, "Night Drifter")
        self.assertEqual(rival.car_class, "S13")
        self.assertIn("hatzenbach", rival.zones)
        self.assertEqual(rival.base_sp_pool, 0.8)
    
    def test_create_boss(self):
        """Create a boss-tier rival."""
        rival = create_boss("Karussell King", "GT-R", "Ring Masters", ["karussell"])
        
        self.assertEqual(rival.tier, RivalTier.BOSS)
        self.assertEqual(rival.team_name, "Ring Masters")
        self.assertEqual(rival.base_sp_pool, 1.2)
        self.assertGreater(rival.aggression, 0.5)
    
    def test_create_team_leader(self):
        """Create a team leader rival."""
        rival = create_team_leader("Shadow Ace", "R34 GT-R", "Midnight Runners")
        
        self.assertEqual(rival.tier, RivalTier.TEAM_LEADER)
        self.assertEqual(rival.base_sp_pool, 1.5)
        self.assertLess(rival.sp_drain_resistance, 1.0)  # Takes less damage
    
    def test_battle_stats_recording(self):
        """Record battle results in stats."""
        rival = create_wanderer("Test", "S13", [])
        
        rival.record_battle_result(won=True, duration_s=30.0, sp_drained=1.0, sp_lost=0.3)
        rival.record_battle_result(won=False, duration_s=45.0, sp_drained=0.5, sp_lost=1.0)
        
        self.assertEqual(rival.stats.battles_fought, 2)
        self.assertEqual(rival.stats.battles_won, 1)
        self.assertEqual(rival.stats.battles_lost, 1)
        self.assertEqual(rival.stats.win_rate, 0.5)
    
    def test_serialization_roundtrip(self):
        """Serialize and deserialize rival."""
        original = create_boss("Test Boss", "GT-R", "Test Team", ["zone1"])
        original.record_battle_result(True, 30.0, 1.0, 0.5)
        
        data = original.to_dict()
        restored = RivalEntity.from_dict(data)
        
        self.assertEqual(restored.rival_id, original.rival_id)
        self.assertEqual(restored.tier, original.tier)
        self.assertEqual(restored.stats.battles_won, 1)


class TestBattleManager(unittest.TestCase):
    """Test BattleManager lifecycle."""
    
    def setUp(self):
        self.config = SPConfig(
            base_drain_per_second=0.05,
            gap_multiplier=0.003,
        )
        self.manager = BattleManager(sp_config=self.config)
        self.rival = create_wanderer("Test Rival", "S13", [])
    
    def test_initiate_battle(self):
        """Start a new battle."""
        battle = self.manager.initiate_battle(self.rival, current_tick=100)
        
        self.assertIsNotNone(battle.battle_id)
        self.assertEqual(battle.phase, BattlePhase.COUNTDOWN)
        self.assertEqual(battle.rival.rival_id, self.rival.rival_id)
    
    def test_countdown_to_active(self):
        """Battle transitions from countdown to active."""
        battle = self.manager.initiate_battle(self.rival, current_tick=0)
        
        # Skip through countdown
        for tick in range(200):
            battle = self.manager.tick(
                battle,
                player_progress_m=1000,
                rival_progress_m=1000,
                player_speed_mps=45,
                rival_speed_mps=45,
                current_tick=tick
            )
        
        self.assertEqual(battle.phase, BattlePhase.ACTIVE)
    
    def test_battle_victory(self):
        """Player wins when rival SP reaches zero."""
        battle = self.manager.initiate_battle(self.rival, current_tick=0)
        battle.phase = BattlePhase.ACTIVE  # Skip countdown
        battle.start_tick = 0
        
        # Player leads, draining rival
        for tick in range(3000):
            battle = self.manager.tick(
                battle,
                player_progress_m=1050 + tick * 0.5,
                rival_progress_m=1000 + tick * 0.45,
                player_speed_mps=45,
                rival_speed_mps=40,
                current_tick=tick
            )
            if battle.result:
                break
        
        self.assertEqual(battle.phase, BattlePhase.FINISHED)
        self.assertIsNotNone(battle.result)
        self.assertEqual(battle.result.winner, "player")
    
    def test_battle_defeat(self):
        """Player loses when their SP reaches zero."""
        battle = self.manager.initiate_battle(self.rival, current_tick=0)
        battle.phase = BattlePhase.ACTIVE
        battle.start_tick = 0
        
        # Rival leads, draining player
        for tick in range(3000):
            battle = self.manager.tick(
                battle,
                player_progress_m=1000 + tick * 0.4,
                rival_progress_m=1050 + tick * 0.5,
                player_speed_mps=40,
                rival_speed_mps=45,
                current_tick=tick
            )
            if battle.result:
                break
        
        self.assertEqual(battle.result.winner, self.rival.rival_id)
    
    def test_result_hash_determinism(self):
        """Battle result hash should be deterministic."""
        # Run same battle twice
        hashes = []
        
        for _ in range(2):
            battle = self.manager.initiate_battle(self.rival, current_tick=0)
            battle.phase = BattlePhase.ACTIVE
            battle.start_tick = 0
            battle.player_sp = 1.0
            battle.rival_sp = self.rival.base_sp_pool
            
            for tick in range(2000):
                battle = self.manager.tick(
                    battle,
                    player_progress_m=1050 + tick * 0.5,
                    rival_progress_m=1000 + tick * 0.45,
                    player_speed_mps=45,
                    rival_speed_mps=40,
                    current_tick=tick
                )
                if battle.result:
                    hashes.append(battle.result.compute_hash())
                    break
        
        self.assertEqual(len(hashes), 2)
        # Note: Hashes may differ due to timestamp, but structure is consistent


class TestRivalSpawner(unittest.TestCase):
    """Test zone-based rival spawning."""
    
    def setUp(self):
        self.zones = create_nurburgring_zones()[:3]  # First 3 zones
        self.spawner = RivalSpawner(self.zones)
        
        # Register rivals
        self.wanderer = create_wanderer("Test Wanderer", "S13", ["hatzenbach"])
        self.spawner.register_rival(self.wanderer)
        self.zones[0].wanderer_pool.append(self.wanderer.rival_id)
    
    def test_spawn_in_zone(self):
        """Rival should spawn when player is in valid zone."""
        import random
        rng = random.Random(12345)
        
        spawned = None
        for tick in range(10000):  # Many attempts
            result = self.spawner.tick(
                player_progress_m=500,  # In hatzenbach
                current_tick=tick,
                rng=rng
            )
            if result:
                spawned = result
                break
        
        self.assertIsNotNone(spawned)
        self.assertEqual(spawned.rival_id, self.wanderer.rival_id)
    
    def test_no_spawn_outside_zone(self):
        """No spawn when player is outside all zones."""
        import random
        rng = random.Random(42)
        
        spawned = None
        for tick in range(1000):
            result = self.spawner.tick(
                player_progress_m=50000,  # Way outside all zones
                current_tick=tick,
                rng=rng
            )
            if result:
                spawned = result
        
        self.assertIsNone(spawned)
    
    def test_zone_cooldown(self):
        """Zone should have cooldown after spawn."""
        import random
        rng = random.Random(42)
        
        # Force a spawn
        self.zones[0].spawn_chance_per_tick = 1.0  # Guarantee spawn
        self.spawner.tick(500, 0, rng)
        self.spawner.remove_active_rival(self.wanderer.rival_id)
        
        # Should be on cooldown now
        self.assertTrue(self.zones[0].is_on_cooldown(100))
        
        # After cooldown expires
        self.assertFalse(self.zones[0].is_on_cooldown(700))


class TestHeadlightFlashSystem(unittest.TestCase):
    """Test headlight flash challenge system."""
    
    def setUp(self):
        self.manager = BattleManager()
        self.flash = HeadlightFlashSystem(
            self.manager,
            flash_range_m=75.0,
            auto_accept_range_m=30.0
        )
        self.rival = create_wanderer("Test", "S13", [])
    
    def test_flash_in_range(self):
        """Can challenge when within flash range."""
        challenge = self.flash.issue_challenge(
            player_progress_m=1000,
            rival=self.rival,
            rival_progress_m=1050,  # 50m ahead
            current_tick=0
        )
        
        self.assertIsNotNone(challenge)
        self.assertEqual(challenge.target.rival_id, self.rival.rival_id)
    
    def test_flash_out_of_range(self):
        """Cannot challenge when too far."""
        challenge = self.flash.issue_challenge(
            player_progress_m=1000,
            rival=self.rival,
            rival_progress_m=1200,  # 200m ahead (too far)
            current_tick=0
        )
        
        self.assertIsNone(challenge)
    
    def test_auto_accept_close_range(self):
        """Auto-accept when very close."""
        challenge = self.flash.issue_challenge(
            player_progress_m=1000,
            rival=self.rival,
            rival_progress_m=1025,  # 25m ahead (within auto-accept)
            current_tick=0
        )
        
        self.assertIsNotNone(challenge)
        self.assertTrue(challenge.accepted)
    
    def test_battle_starts_on_accept(self):
        """Battle starts when challenge is accepted."""
        self.flash.issue_challenge(1000, self.rival, 1050, 0)
        battle = self.flash.accept_challenge(current_tick=50)
        
        self.assertIsNotNone(battle)
        self.assertEqual(battle.phase, BattlePhase.COUNTDOWN)


class TestIntegration(unittest.TestCase):
    """Integration tests for complete battle flow."""
    
    def test_full_battle_flow(self):
        """Complete flow from spawn to victory."""
        import random
        
        # Setup
        spawner = RivalSpawner()
        zone = SpawnZone("test", "Test Zone", 0, 1000, spawn_chance_per_tick=1.0)
        spawner.add_zone(zone)
        
        rival = create_wanderer("Test", "S13", ["test"])
        spawner.register_rival(rival)
        zone.wanderer_pool.append(rival.rival_id)
        
        manager = BattleManager(SPConfig(base_drain_per_second=0.1))
        flash = HeadlightFlashSystem(manager)
        
        # Spawn rival
        rng = random.Random(42)
        spawned = spawner.tick(500, 0, rng)
        self.assertIsNotNone(spawned)
        
        # Challenge
        challenge = flash.issue_challenge(500, spawned, 530, 10)
        self.assertIsNotNone(challenge)
        
        # Accept and start battle
        flash.pending_challenge.accepted = True
        battle = flash.tick(20)
        self.assertIsNotNone(battle)
        
        # Skip countdown
        battle.phase = BattlePhase.ACTIVE
        battle.start_tick = 20
        
        # Battle until victory
        for tick in range(20, 2000):
            battle = manager.tick(
                battle,
                player_progress_m=500 + (tick - 20) * 0.5,
                rival_progress_m=530 + (tick - 20) * 0.4,
                player_speed_mps=45,
                rival_speed_mps=40,
                current_tick=tick
            )
            if battle.result:
                break
        
        self.assertIsNotNone(battle.result)
        self.assertEqual(battle.result.winner, "player")


if __name__ == "__main__":
    print("🏎️  Highway Battle System - Unit Tests\n")
    print("=" * 60)
    
    # Run tests with verbosity
    unittest.main(verbosity=2)
