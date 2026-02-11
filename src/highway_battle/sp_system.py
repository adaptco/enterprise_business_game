"""
SP (Spirit Points) System - Core battle mechanics.

The SP bar is the "health" system in Tokyo Extreme Racer-style battles:
- Both cars start with full SP (1.0)
- Being behind drains your SP
- Speed differential amplifies drain
- First to reach 0 SP loses

This implementation is deterministic for replay verification.
"""

from dataclasses import dataclass, field
from typing import Tuple
import hashlib
import json


@dataclass
class SPConfig:
    """Configuration for SP drain mechanics."""
    
    # Base drain rate (per second) when behind
    base_drain_per_second: float = 0.03
    
    # Drain multiplier per meter of gap
    gap_multiplier: float = 0.002
    
    # Drain multiplier per m/s speed difference
    speed_multiplier: float = 0.008
    
    # Escalation rate (drain increases over battle duration)
    escalation_rate: float = 0.0002
    
    # Physics tick rate
    tick_rate_hz: float = 60.0
    
    # Minimum SP drain per tick (prevents stalemates)
    min_drain_per_tick: float = 0.0001
    
    # Maximum SP drain per tick (prevents instant kills)
    max_drain_per_tick: float = 0.01
    
    # Critical SP threshold (triggers warning)
    critical_threshold: float = 0.25
    
    def to_dict(self) -> dict:
        return {
            "base_drain_per_second": self.base_drain_per_second,
            "gap_multiplier": self.gap_multiplier,
            "speed_multiplier": self.speed_multiplier,
            "escalation_rate": self.escalation_rate,
            "tick_rate_hz": self.tick_rate_hz,
            "min_drain_per_tick": self.min_drain_per_tick,
            "max_drain_per_tick": self.max_drain_per_tick,
            "critical_threshold": self.critical_threshold,
        }


@dataclass
class SPState:
    """Current SP state for both combatants."""
    
    player_sp: float = 1.0
    rival_sp: float = 1.0
    player_is_leader: bool = False
    gap_meters: float = 0.0
    speed_diff_mps: float = 0.0
    battle_duration_s: float = 0.0
    total_drain_player: float = 0.0
    total_drain_rival: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "player_sp": round(self.player_sp, 4),
            "rival_sp": round(self.rival_sp, 4),
            "player_is_leader": self.player_is_leader,
            "gap_meters": round(self.gap_meters, 2),
            "speed_diff_mps": round(self.speed_diff_mps, 2),
            "battle_duration_s": round(self.battle_duration_s, 2),
            "total_drain_player": round(self.total_drain_player, 4),
            "total_drain_rival": round(self.total_drain_rival, 4),
        }
    
    def compute_hash(self) -> str:
        """Compute deterministic hash for SSOT verification."""
        canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]


class SPSystem:
    """
    Spirit Points battle mechanics engine.
    
    Deterministic calculation of SP drain based on:
    - Gap distance (leader advantage)
    - Speed differential
    - Battle duration (escalation)
    
    Usage:
        sp = SPSystem(SPConfig())
        
        for tick in battle_loop:
            state = sp.tick(
                player_progress_m=1500.0,
                rival_progress_m=1485.0,
                player_speed_mps=45.0,
                rival_speed_mps=42.0
            )
            
            if state.player_sp <= 0:
                print("Player defeated!")
            elif state.rival_sp <= 0:
                print("Player wins!")
    """
    
    def __init__(self, config: SPConfig=None):
        self.config = config or SPConfig()
        self._state = SPState()
        self._tick_count = 0
    
    def reset(self, player_sp: float=1.0, rival_sp: float=1.0):
        """Reset SP state for new battle."""
        self._state = SPState(player_sp=player_sp, rival_sp=rival_sp)
        self._tick_count = 0
    
    def tick(
        self,
        player_progress_m: float,
        rival_progress_m: float,
        player_speed_mps: float,
        rival_speed_mps: float,
    ) -> SPState:
        """
        Process one tick of SP calculation.
        
        Args:
            player_progress_m: Player's track progress in meters
            rival_progress_m: Rival's track progress in meters
            player_speed_mps: Player's current speed in m/s
            rival_speed_mps: Rival's current speed in m/s
            
        Returns:
            Updated SPState
        """
        self._tick_count += 1
        
        # Calculate gap and leader
        gap = player_progress_m - rival_progress_m
        player_is_leader = gap >= 0
        gap_meters = abs(gap)
        
        # Calculate speed difference (positive = leader is faster)
        if player_is_leader:
            speed_diff = player_speed_mps - rival_speed_mps
        else:
            speed_diff = rival_speed_mps - player_speed_mps
        
        # Update duration
        battle_duration_s = self._tick_count / self.config.tick_rate_hz
        
        # Calculate drain for trailing car
        drain = self._compute_drain(gap_meters, speed_diff, battle_duration_s)
        
        # Apply drain to trailing car
        if player_is_leader:
            self._state.rival_sp = max(0.0, self._state.rival_sp - drain)
            self._state.total_drain_rival += drain
        else:
            self._state.player_sp = max(0.0, self._state.player_sp - drain)
            self._state.total_drain_player += drain
        
        # Update state
        self._state.player_is_leader = player_is_leader
        self._state.gap_meters = gap_meters
        self._state.speed_diff_mps = speed_diff
        self._state.battle_duration_s = battle_duration_s
        
        return self._state
    
    def _compute_drain(
        self,
        gap_meters: float,
        speed_diff_mps: float,
        battle_duration_s: float,
    ) -> float:
        """
        Compute SP drain for trailing car.
        
        Formula:
            drain = (base + gap_factor + speed_factor) * escalation
        """
        cfg = self.config
        tick_factor = 1.0 / cfg.tick_rate_hz
        
        # Base drain
        base_drain = cfg.base_drain_per_second * tick_factor
        
        # Gap-based drain (being further behind hurts more)
        gap_drain = gap_meters * cfg.gap_multiplier * tick_factor
        
        # Speed-based drain (leader pulling away hurts more)
        speed_drain = max(0, speed_diff_mps) * cfg.speed_multiplier * tick_factor
        
        # Escalation (battles get more intense over time)
        escalation = 1.0 + (battle_duration_s * cfg.escalation_rate)
        
        # Total drain
        total_drain = (base_drain + gap_drain + speed_drain) * escalation
        
        # Clamp to configured bounds
        return max(cfg.min_drain_per_tick, min(cfg.max_drain_per_tick, total_drain))
    
    def get_state(self) -> SPState:
        """Get current SP state."""
        return self._state
    
    def is_player_critical(self) -> bool:
        """Check if player SP is critically low."""
        return self._state.player_sp <= self.config.critical_threshold
    
    def is_rival_critical(self) -> bool:
        """Check if rival SP is critically low."""
        return self._state.rival_sp <= self.config.critical_threshold
    
    def get_winner(self) -> str | None:
        """
        Check if battle has ended.
        
        Returns:
            "player" if player wins, "rival" if rival wins, None if ongoing
        """
        if self._state.rival_sp <= 0:
            return "player"
        elif self._state.player_sp <= 0:
            return "rival"
        return None


# Standalone test
if __name__ == "__main__":
    print("🏎️  SP System Test\n")
    
    sp = SPSystem(SPConfig(
        base_drain_per_second=0.05,
        gap_multiplier=0.003,
        speed_multiplier=0.01,
    ))
    
    # Simulate a battle where player pulls ahead
    for tick in range(600):  # 10 seconds at 60Hz
        # Player gradually pulls ahead
        player_progress = 1000 + tick * 0.75  # ~45 m/s
        rival_progress = 1000 + tick * 0.70  # ~42 m/s
        
        state = sp.tick(
            player_progress_m=player_progress,
            rival_progress_m=rival_progress,
            player_speed_mps=45.0,
            rival_speed_mps=42.0,
        )
        
        if tick % 60 == 0:
            print(f"  t={tick/60:.1f}s | Player SP: {state.player_sp:.2f} | "
                  f"Rival SP: {state.rival_sp:.2f} | Gap: {state.gap_meters:.1f}m")
        
        winner = sp.get_winner()
        if winner:
            print(f"\n🏁 Battle ended at tick {tick}! Winner: {winner.upper()}")
            break
    
    print(f"\n📊 Final state hash: {state.compute_hash()}")
