"""
Battle Manager - Core 1v1 highway duel orchestration.

Manages the complete battle lifecycle:
1. Battle initiation (headlight flash challenge)
2. Tick-by-tick SP calculation
3. Victory/defeat detection
4. Battle result logging for SSOT
"""

from dataclasses import dataclass, field
from typing import Optional, List, Callable
from enum import Enum
import hashlib
import json
import uuid
from datetime import datetime, timezone

from .sp_system import SPSystem, SPConfig, SPState
from .rival_entity import RivalEntity, RivalTier


class BattlePhase(Enum):
    """Battle lifecycle phases."""
    
    PENDING = "pending"  # Challenge issued, waiting for accept
    COUNTDOWN = "countdown"  # 3-2-1 countdown
    ACTIVE = "active"  # Battle in progress
    FINISHED = "finished"  # Battle complete


@dataclass
class BattleResult:
    """Final battle outcome."""
    
    battle_id: str
    winner: str  # "player" or rival_id
    loser: str
    duration_ticks: int
    duration_seconds: float
    final_sp_winner: float
    final_sp_loser: float
    total_sp_drained_winner: float
    total_sp_drained_loser: float
    rival_tier: str
    timestamp: str
    
    def to_dict(self) -> dict:
        return {
            "battle_id": self.battle_id,
            "winner": self.winner,
            "loser": self.loser,
            "duration_ticks": self.duration_ticks,
            "duration_seconds": round(self.duration_seconds, 2),
            "final_sp_winner": round(self.final_sp_winner, 4),
            "final_sp_loser": round(self.final_sp_loser, 4),
            "total_sp_drained_winner": round(self.total_sp_drained_winner, 4),
            "total_sp_drained_loser": round(self.total_sp_drained_loser, 4),
            "rival_tier": self.rival_tier,
            "timestamp": self.timestamp,
        }
    
    def compute_hash(self) -> str:
        """Compute deterministic hash for SSOT."""
        canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]


@dataclass
class BattleState:
    """Active battle state."""
    
    battle_id: str
    rival: RivalEntity
    phase: BattlePhase = BattlePhase.PENDING
    start_tick: int = 0
    current_tick: int = 0
    
    # SP state (updated each tick)
    player_sp: float = 1.0
    rival_sp: float = 1.0
    
    # Current frame data
    player_progress_m: float = 0.0
    rival_progress_m: float = 0.0
    player_speed_mps: float = 0.0
    rival_speed_mps: float = 0.0
    gap_meters: float = 0.0
    player_is_leader: bool = False
    
    # Battle events log
    events: List[dict] = field(default_factory=list)
    
    # Result (set when finished)
    result: Optional[BattleResult] = None
    
    def to_dict(self) -> dict:
        return {
            "battle_id": self.battle_id,
            "rival_id": self.rival.rival_id,
            "rival_name": self.rival.name,
            "phase": self.phase.value,
            "current_tick": self.current_tick,
            "player_sp": round(self.player_sp, 4),
            "rival_sp": round(self.rival_sp, 4),
            "gap_meters": round(self.gap_meters, 2),
            "player_is_leader": self.player_is_leader,
        }


class BattleManager:
    """
    Manages highway battle encounters.
    
    Usage:
        manager = BattleManager()
        
        # Start a battle
        battle = manager.initiate_battle(rival, current_tick=1000)
        
        # Each tick
        battle = manager.tick(
            battle,
            player_progress_m=1500.0,
            rival_progress_m=1485.0,
            player_speed_mps=45.0,
            rival_speed_mps=42.0,
            current_tick=1001
        )
        
        # Check for completion
        if battle.result:
            print(f"Winner: {battle.result.winner}")
    """
    
    def __init__(
        self,
        sp_config: SPConfig=None,
        tick_rate_hz: float=60.0,
        countdown_ticks: int=180,  # 3 seconds at 60Hz
    ):
        self.sp_config = sp_config or SPConfig()
        self.tick_rate_hz = tick_rate_hz
        self.countdown_ticks = countdown_ticks
        
        # Event callbacks
        self._on_battle_start: List[Callable] = []
        self._on_battle_end: List[Callable] = []
        self._on_sp_critical: List[Callable] = []
    
    def initiate_battle(
        self,
        rival: RivalEntity,
        current_tick: int,
        player_start_sp: float=1.0,
    ) -> BattleState:
        """
        Start a new battle with a rival.
        
        Args:
            rival: The rival to battle
            current_tick: Current simulation tick
            player_start_sp: Player's starting SP (usually 1.0)
            
        Returns:
            New BattleState in COUNTDOWN phase
        """
        battle_id = f"battle_{uuid.uuid4().hex[:8]}"
        
        # Reset rival for battle
        rival.reset_for_battle()
        
        state = BattleState(
            battle_id=battle_id,
            rival=rival,
            phase=BattlePhase.COUNTDOWN,
            start_tick=current_tick,
            current_tick=current_tick,
            player_sp=player_start_sp,
            rival_sp=rival.base_sp_pool,
        )
        
        state.events.append({
            "tick": current_tick,
            "event": "battle_initiated",
            "rival_id": rival.rival_id,
            "rival_name": rival.name,
        })
        
        return state
    
    def tick(
        self,
        state: BattleState,
        player_progress_m: float,
        rival_progress_m: float,
        player_speed_mps: float,
        rival_speed_mps: float,
        current_tick: int,
    ) -> BattleState:
        """
        Process one tick of the battle.
        
        Args:
            state: Current battle state
            player_progress_m: Player's track progress in meters
            rival_progress_m: Rival's track progress in meters
            player_speed_mps: Player's current speed
            rival_speed_mps: Rival's current speed
            current_tick: Current simulation tick
            
        Returns:
            Updated BattleState
        """
        state.current_tick = current_tick
        state.player_progress_m = player_progress_m
        state.rival_progress_m = rival_progress_m
        state.player_speed_mps = player_speed_mps
        state.rival_speed_mps = rival_speed_mps
        
        # Handle countdown phase
        if state.phase == BattlePhase.COUNTDOWN:
            countdown_elapsed = current_tick - state.start_tick
            if countdown_elapsed >= self.countdown_ticks:
                state.phase = BattlePhase.ACTIVE
                state.start_tick = current_tick  # Reset for battle duration
                state.events.append({
                    "tick": current_tick,
                    "event": "battle_started",
                })
                for callback in self._on_battle_start:
                    callback(state)
            return state
        
        # Skip if not active
        if state.phase != BattlePhase.ACTIVE:
            return state
        
        # Calculate gap and leader
        gap = player_progress_m - rival_progress_m
        state.player_is_leader = gap >= 0
        state.gap_meters = abs(gap)
        
        # Compute SP drain
        drain = self._compute_drain(state)
        
        # Track previous SP for critical detection
        prev_player_sp = state.player_sp
        prev_rival_sp = state.rival_sp
        
        # Apply drain to trailing car
        if state.player_is_leader:
            state.rival_sp = max(0.0, state.rival_sp - drain)
        else:
            state.player_sp = max(0.0, state.player_sp - drain)
        
        # Check for critical SP events
        critical_threshold = self.sp_config.critical_threshold
        if prev_player_sp > critical_threshold and state.player_sp <= critical_threshold:
            state.events.append({"tick": current_tick, "event": "player_sp_critical"})
            for callback in self._on_sp_critical:
                callback(state, "player")
        
        if prev_rival_sp > critical_threshold and state.rival_sp <= critical_threshold:
            state.events.append({"tick": current_tick, "event": "rival_sp_critical"})
            for callback in self._on_sp_critical:
                callback(state, "rival")
        
        # Check for victory
        if state.rival_sp <= 0:
            state = self._end_battle(state, winner="player")
        elif state.player_sp <= 0:
            state = self._end_battle(state, winner=state.rival.rival_id)
        
        return state
    
    def _compute_drain(self, state: BattleState) -> float:
        """Compute SP drain for this tick."""
        cfg = self.sp_config
        tick_factor = 1.0 / self.tick_rate_hz
        
        # Battle duration for escalation
        battle_ticks = state.current_tick - state.start_tick
        battle_duration_s = battle_ticks / self.tick_rate_hz
        
        # Speed difference (positive = leader is faster)
        if state.player_is_leader:
            speed_diff = state.player_speed_mps - state.rival_speed_mps
        else:
            speed_diff = state.rival_speed_mps - state.player_speed_mps
        
        # Compute drain components
        base_drain = cfg.base_drain_per_second * tick_factor
        gap_drain = state.gap_meters * cfg.gap_multiplier * tick_factor
        speed_drain = max(0, speed_diff) * cfg.speed_multiplier * tick_factor
        escalation = 1.0 + (battle_duration_s * cfg.escalation_rate)
        
        total_drain = (base_drain + gap_drain + speed_drain) * escalation
        
        return max(cfg.min_drain_per_tick, min(cfg.max_drain_per_tick, total_drain))
    
    def _end_battle(self, state: BattleState, winner: str) -> BattleState:
        """Finalize battle with result."""
        state.phase = BattlePhase.FINISHED
        
        battle_ticks = state.current_tick - state.start_tick
        battle_duration_s = battle_ticks / self.tick_rate_hz
        
        is_player_winner = winner == "player"
        loser = state.rival.rival_id if is_player_winner else "player"
        
        state.result = BattleResult(
            battle_id=state.battle_id,
            winner=winner,
            loser=loser,
            duration_ticks=battle_ticks,
            duration_seconds=battle_duration_s,
            final_sp_winner=state.player_sp if is_player_winner else state.rival_sp,
            final_sp_loser=state.rival_sp if is_player_winner else state.player_sp,
            total_sp_drained_winner=1.0 - state.rival_sp if is_player_winner else 1.0 - state.player_sp,
            total_sp_drained_loser=1.0 - state.player_sp if is_player_winner else 1.0 - state.rival_sp,
            rival_tier=state.rival.tier.name,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
        state.events.append({
            "tick": state.current_tick,
            "event": "battle_finished",
            "winner": winner,
            "result_hash": state.result.compute_hash(),
        })
        
        # Update rival stats
        state.rival.record_battle_result(
            won=not is_player_winner,
            duration_s=battle_duration_s,
            sp_drained=state.result.total_sp_drained_winner if not is_player_winner else state.result.total_sp_drained_loser,
            sp_lost=state.result.total_sp_drained_loser if not is_player_winner else state.result.total_sp_drained_winner,
        )
        
        # Fire callbacks
        for callback in self._on_battle_end:
            callback(state)
        
        return state
    
    def on_battle_start(self, callback: Callable):
        """Register callback for battle start."""
        self._on_battle_start.append(callback)
    
    def on_battle_end(self, callback: Callable):
        """Register callback for battle end."""
        self._on_battle_end.append(callback)
    
    def on_sp_critical(self, callback: Callable):
        """Register callback for SP critical events."""
        self._on_sp_critical.append(callback)


# Standalone test
if __name__ == "__main__":
    from .rival_entity import create_boss
    
    print("🏎️  Battle Manager Test\n")
    
    # Create a boss rival
    rival = create_boss(
        name="Karussell King",
        car_class="GT-R",
        team_name="Ring Masters",
        zones=["karussell"],
    )
    
    # Create battle manager
    manager = BattleManager(SPConfig(
        base_drain_per_second=0.05,
        gap_multiplier=0.003,
    ))
    
    # Register callbacks
    manager.on_battle_end(lambda s: print(f"  🏁 Battle ended! Winner: {s.result.winner}"))
    
    # Initiate battle
    battle = manager.initiate_battle(rival, current_tick=0)
    print(f"  Battle initiated: {battle.battle_id}")
    print(f"  Rival: {rival.display_name}")
    
    # Skip countdown
    battle.phase = BattlePhase.ACTIVE
    battle.start_tick = 0
    
    # Simulate battle
    print("\n  Simulating battle...")
    for tick in range(1200):  # 20 seconds max
        # Player gradually pulls ahead
        player_progress = 1000 + tick * 0.75
        rival_progress = 1000 + tick * 0.70
        
        battle = manager.tick(
            battle,
            player_progress_m=player_progress,
            rival_progress_m=rival_progress,
            player_speed_mps=45.0,
            rival_speed_mps=42.0,
            current_tick=tick,
        )
        
        if tick % 120 == 0:
            print(f"    t={tick/60:.1f}s | Player: {battle.player_sp:.2f} | "
                  f"Rival: {battle.rival_sp:.2f} | Gap: {battle.gap_meters:.1f}m")
        
        if battle.result:
            break
    
    if battle.result:
        print(f"\n  📊 Result: {battle.result.to_dict()}")
        print(f"  Result Hash: {battle.result.compute_hash()}")
