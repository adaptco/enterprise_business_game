"""
Unit tests for Racing Simulator Physics Enhancements.
Tests tire degradation, fuel consumption, and dynamic weather effects.
"""

import sys
import unittest
import hashlib
import json
import os

# Add src path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from racing_simulator import (
    RacingSimulator,
    ControlInput,
    TireCompound,
    TireState,
    FuelState,
    WeatherState,
    DeterministicVehiclePhysics
)


class TestTireDegradation(unittest.TestCase):
    """Tests for tire wear mechanics."""
    
    def test_tire_wear_increases_with_throttle(self):
        """Tire wear should increase with aggressive throttle usage."""
        sim = RacingSimulator(seed=42, enable_weather=False)
        initial_wear = sim.physics.tire_state.wear
        
        # Run 100 steps at full throttle
        control = ControlInput(steering_command=0.0, throttle_command=1.0, brake_command=0.0)
        for _ in range(100):
            sim.step(control)
        
        final_wear = sim.physics.tire_state.wear
        self.assertGreater(final_wear, initial_wear)
        self.assertGreater(final_wear, 0.1, "Expected significant wear after 100 steps at full throttle")
        print(f"\n✅ Tire wear test: {initial_wear:.4f} → {final_wear:.4f}")
    
    def test_soft_tires_degrade_faster(self):
        """Soft compound should wear faster than hard compound."""
        # Soft tires
        sim_soft = RacingSimulator(seed=42, tire_compound=TireCompound.SOFT, enable_weather=False)
        # Hard tires
        sim_hard = RacingSimulator(seed=42, tire_compound=TireCompound.HARD, enable_weather=False)
        
        control = ControlInput(steering_command=0.0, throttle_command=0.8, brake_command=0.0)
        for _ in range(200):
            sim_soft.step(control)
            sim_hard.step(control)
        
        soft_wear = sim_soft.physics.tire_state.wear
        hard_wear = sim_hard.physics.tire_state.wear
        
        self.assertGreater(soft_wear, hard_wear)
        print(f"\n✅ Compound wear test: Soft={soft_wear:.4f}, Hard={hard_wear:.4f}")
    
    def test_tire_grip_decreases_with_wear(self):
        """Grip multiplier should decrease as tires wear."""
        tire = TireState(compound=TireCompound.MEDIUM, wear=0.0)
        fresh_grip = tire.grip_multiplier
        
        tire.wear = 0.5
        worn_grip = tire.grip_multiplier
        
        tire.wear = 1.0
        dead_grip = tire.grip_multiplier
        
        self.assertGreater(fresh_grip, worn_grip)
        self.assertGreater(worn_grip, dead_grip)
        self.assertGreaterEqual(dead_grip, 0.3, "Grip should have a minimum floor")
        print(f"\n✅ Grip degradation: Fresh={fresh_grip:.3f}, 50%={worn_grip:.3f}, 100%={dead_grip:.3f}")


class TestFuelConsumption(unittest.TestCase):
    """Tests for fuel consumption mechanics."""
    
    def test_fuel_decreases_over_time(self):
        """Fuel should decrease during racing."""
        sim = RacingSimulator(seed=42, enable_weather=False)
        initial_fuel = sim.physics.fuel_state.current_kg
        
        control = ControlInput(steering_command=0.0, throttle_command=0.7, brake_command=0.0)
        for _ in range(500):
            sim.step(control)
        
        final_fuel = sim.physics.fuel_state.current_kg
        self.assertLess(final_fuel, initial_fuel)
        print(f"\n✅ Fuel consumption: {initial_fuel:.1f}kg → {final_fuel:.1f}kg")
    
    def test_fuel_mass_penalty(self):
        """Heavy fuel load should penalize acceleration."""
        # Full tank
        fuel_full = FuelState(current_kg=110.0, max_kg=110.0)
        # Empty tank
        fuel_empty = FuelState(current_kg=0.0, max_kg=110.0)
        
        self.assertGreater(fuel_full.mass_penalty, fuel_empty.mass_penalty)
        self.assertEqual(fuel_empty.mass_penalty, 0.0)
        self.assertAlmostEqual(fuel_full.mass_penalty, 0.02, places=3)
        print(f"\n✅ Mass penalty: Full={fuel_full.mass_penalty:.4f}, Empty={fuel_empty.mass_penalty:.4f}")


class TestWeatherEffects(unittest.TestCase):
    """Tests for dynamic weather system."""
    
    def test_rain_reduces_grip(self):
        """Rain should reduce track grip."""
        weather = WeatherState(grip_mu=1.2, rain_intensity=0.0)
        dry_grip = weather.grip_mu
        
        # Simulate rain
        weather.rain_intensity = 0.8
        import numpy as np
        rng = np.random.RandomState(42)
        for _ in range(50):
            weather.tick(rng)
        
        wet_grip = weather.grip_mu
        self.assertLess(wet_grip, dry_grip)
        print(f"\n✅ Rain effect: Dry={dry_grip:.2f}, Wet={wet_grip:.2f}")
    
    def test_weather_state_in_vehicle_state(self):
        """Vehicle state should include weather information."""
        sim = RacingSimulator(seed=42, enable_weather=True)
        control = ControlInput(steering_command=0.0, throttle_command=0.5, brake_command=0.0)
        state = sim.step(control)
        
        self.assertIsNotNone(state.weather_grip)
        self.assertIsNotNone(state.rain_intensity)
        print(f"\n✅ Weather in state: grip={state.weather_grip:.2f}, rain={state.rain_intensity:.2f}")


class TestPitStop(unittest.TestCase):
    """Tests for pit stop mechanics."""
    
    def test_pit_stop_resets_tires(self):
        """Pit stop should install fresh tires."""
        sim = RacingSimulator(seed=42, enable_weather=False)
        
        # Wear tires
        control = ControlInput(steering_command=0.0, throttle_command=1.0, brake_command=0.0)
        for _ in range(200):
            sim.step(control)
        
        worn_wear = sim.physics.tire_state.wear
        self.assertGreater(worn_wear, 0.1)
        
        # Pit stop
        sim.pit_stop(new_compound=TireCompound.HARD, fuel_kg=50.0)
        
        self.assertEqual(sim.physics.tire_state.wear, 0.0)
        self.assertEqual(sim.physics.tire_state.compound, TireCompound.HARD)
        self.assertEqual(sim.physics.fuel_state.current_kg, 50.0)
        print(f"\n✅ Pit stop: Wear {worn_wear:.4f} → 0.0, compound=HARD, fuel=50.0kg")
    
    def test_pit_time_penalty(self):
        """Pit entry should impose 25s time penalty."""
        sim = RacingSimulator(seed=42, enable_weather=False)
        
        self.assertFalse(sim.in_pit)
        self.assertEqual(sim.pit_remaining_time, 0.0)
        
        # Trigger pit entry
        sim.trigger_pit_entry(TireCompound.MEDIUM, 80.0)
        
        self.assertTrue(sim.in_pit)
        self.assertEqual(sim.pit_remaining_time, 25.0)
        self.assertEqual(sim.physics.velocity, 0.0)  # Car stopped
        print(f"\n✅ Pit time penalty: in_pit={sim.in_pit}, remaining={sim.pit_remaining_time}s")
    
    def test_pit_signal_triggers_at_threshold(self):
        """Pit signal > threshold should trigger pit entry."""
        sim = RacingSimulator(seed=42, enable_weather=False)
        
        # Wear tires to lower threshold
        control = ControlInput(steering_command=0.0, throttle_command=1.0, brake_command=0.0)
        for _ in range(400):  # Get wear > 0.6
            sim.step(control)
        
        # With high wear, threshold is 0.7
        state, reward = sim.step_with_pit(control, pit_signal=0.75)
        
        self.assertTrue(sim.in_pit)
        self.assertEqual(reward, -10.0)
        print(f"\n✅ Pit signal trigger: wear={sim.physics.tire_state.wear:.2f}, in_pit=True")
    
    def test_pit_urgency_heuristic(self):
        """Pit urgency should increase with wear and low fuel."""
        # Low urgency
        urgency_low = RacingSimulator.pit_urgency(tire_wear=0.1, fuel_kg=100.0)
        # High urgency
        urgency_high = RacingSimulator.pit_urgency(tire_wear=0.9, fuel_kg=10.0)
        
        self.assertLess(urgency_low, 0.3)
        self.assertGreater(urgency_high, 0.8)
        print(f"\n✅ Pit urgency: low={urgency_low:.2f}, high={urgency_high:.2f}")
    
    def test_get_rl_observation(self):
        """RL observation should be normalized 8-element vector."""
        sim = RacingSimulator(seed=42, enable_weather=True)
        
        control = ControlInput(steering_command=0.0, throttle_command=0.5, brake_command=0.0)
        for _ in range(50):
            sim.step(control)
        
        obs = sim.get_rl_observation()
        
        self.assertEqual(len(obs), 8)
        self.assertTrue(all(0 <= v <= 1.1 for v in obs), "Observations should be normalized")
        print(f"\n✅ RL observation: shape={obs.shape}, values={obs}")


class TestDeterminism(unittest.TestCase):
    """Tests for deterministic replay with degradation."""
    
    def test_identical_runs_produce_same_hash(self):
        """Same seed and inputs should produce identical state hashes."""

        def run_simulation(seed: int):
            sim = RacingSimulator(seed=seed, enable_weather=True)
            control = ControlInput(steering_command=0.1, throttle_command=0.6, brake_command=0.0)
            for _ in range(100):
                sim.step(control)
            checkpoint = sim.create_checkpoint()
            return checkpoint['canonical_sha256']
        
        hash1 = run_simulation(42)
        hash2 = run_simulation(42)
        
        self.assertEqual(hash1, hash2)
        print(f"\n✅ Determinism: hash1={hash1[:16]}... == hash2={hash2[:16]}...")
    
    def test_checkpoint_includes_degradation_state(self):
        """Checkpoint should include tire, fuel, and weather state."""
        sim = RacingSimulator(seed=42, enable_weather=True)
        control = ControlInput(steering_command=0.0, throttle_command=0.5, brake_command=0.0)
        for _ in range(50):
            sim.step(control)
        
        checkpoint = sim.create_checkpoint()
        sv = checkpoint['state_vector']
        
        self.assertIn('tire_wear', sv)
        self.assertIn('tire_compound', sv)
        self.assertIn('fuel_kg', sv)
        self.assertIn('weather_grip', sv)
        self.assertIn('rain_intensity', sv)
        print(f"\n✅ Checkpoint state: tire_wear={sv['tire_wear']:.4f}, fuel={sv['fuel_kg']:.1f}kg")


if __name__ == '__main__':
    print("=" * 60)
    print("  🏎️  Racing Simulator Physics Test Suite")
    print("=" * 60)
    unittest.main(verbosity=2)
