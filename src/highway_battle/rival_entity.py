"""
Rival Entity - AI-controlled opponent cars.

Rivals are the AI opponents in highway battles. Each has:
- Unique identity and visual styling
- Tier (difficulty level)
- AI driver (Random Forest or heuristic)
- SP pool and aggression settings
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple, Optional, Dict, Any
import hashlib
import json
import uuid


class RivalTier(Enum):
    """Rival difficulty tiers."""
    
    WANDERER = 1  # Random encounters, easier
    BOSS = 2  # Named rivals, moderate difficulty
    TEAM_LEADER = 3  # End-game challenges, hardest


@dataclass
class RivalStats:
    """Rival performance statistics."""
    
    battles_fought: int = 0
    battles_won: int = 0
    battles_lost: int = 0
    total_sp_drained: float = 0.0
    total_sp_lost: float = 0.0
    best_victory_time_s: Optional[float] = None
    
    @property
    def win_rate(self) -> float:
        if self.battles_fought == 0:
            return 0.0
        return self.battles_won / self.battles_fought
    
    def to_dict(self) -> dict:
        return {
            "battles_fought": self.battles_fought,
            "battles_won": self.battles_won,
            "battles_lost": self.battles_lost,
            "win_rate": round(self.win_rate, 3),
            "total_sp_drained": round(self.total_sp_drained, 2),
            "total_sp_lost": round(self.total_sp_lost, 2),
            "best_victory_time_s": self.best_victory_time_s,
        }


@dataclass
class RivalEntity:
    """
    AI-controlled rival car.
    
    Represents an opponent in highway battles with unique
    identity, styling, and AI behavior characteristics.
    """
    
    rival_id: str
    name: str
    tier: RivalTier
    car_class: str
    
    # AI driver configuration
    model_path: Optional[str] = None  # Path to RF model, None = heuristic
    aggression: float = 0.5  # 0.0 (cautious) to 1.0 (aggressive)
    skill_level: float = 0.5  # 0.0 (novice) to 1.0 (expert)
    
    # Battle configuration
    base_sp_pool: float = 1.0  # Starting SP (can be > 1.0 for bosses)
    sp_drain_resistance: float = 1.0  # Multiplier on incoming SP drain
    
    # Visual identity
    team_name: Optional[str] = None
    car_color: Tuple[int, int, int] = (128, 128, 128)
    headlight_color: Tuple[int, int, int] = (255, 255, 200)
    
    # Zone restrictions
    zones: list = field(default_factory=list)
    
    # Unlock requirements
    unlock_requirements: Dict[str, Any] = field(default_factory=dict)
    
    # Runtime state
    stats: RivalStats = field(default_factory=RivalStats)
    is_active: bool = False
    current_sp: float = 1.0
    
    def __post_init__(self):
        self.current_sp = self.base_sp_pool
    
    def reset_for_battle(self):
        """Reset state for new battle."""
        self.current_sp = self.base_sp_pool
        self.is_active = True
    
    def apply_sp_drain(self, drain: float):
        """Apply SP drain with resistance."""
        effective_drain = drain * self.sp_drain_resistance
        self.current_sp = max(0.0, self.current_sp - effective_drain)
    
    def record_battle_result(self, won: bool, duration_s: float, sp_drained: float, sp_lost: float):
        """Record battle outcome in stats."""
        self.stats.battles_fought += 1
        if won:
            self.stats.battles_won += 1
            if self.stats.best_victory_time_s is None or duration_s < self.stats.best_victory_time_s:
                self.stats.best_victory_time_s = duration_s
        else:
            self.stats.battles_lost += 1
        
        self.stats.total_sp_drained += sp_drained
        self.stats.total_sp_lost += sp_lost
    
    @property
    def tier_name(self) -> str:
        """Human-readable tier name."""
        return {
            RivalTier.WANDERER: "Wanderer",
            RivalTier.BOSS: "Boss",
            RivalTier.TEAM_LEADER: "Team Leader",
        }.get(self.tier, "Unknown")
    
    @property
    def display_name(self) -> str:
        """Full display name with team."""
        if self.team_name:
            return f"{self.name} ({self.team_name})"
        return self.name
    
    def to_dict(self) -> dict:
        """Export rival data for serialization."""
        return {
            "rival_id": self.rival_id,
            "name": self.name,
            "tier": self.tier.name,
            "car_class": self.car_class,
            "model_path": self.model_path,
            "aggression": self.aggression,
            "skill_level": self.skill_level,
            "base_sp_pool": self.base_sp_pool,
            "sp_drain_resistance": self.sp_drain_resistance,
            "team_name": self.team_name,
            "car_color": list(self.car_color),
            "headlight_color": list(self.headlight_color),
            "zones": self.zones,
            "unlock_requirements": self.unlock_requirements,
            "stats": self.stats.to_dict(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "RivalEntity":
        """Create rival from serialized data."""
        tier = RivalTier[data.get("tier", "WANDERER")]
        
        rival = cls(
            rival_id=data["rival_id"],
            name=data["name"],
            tier=tier,
            car_class=data["car_class"],
            model_path=data.get("model_path"),
            aggression=data.get("aggression", 0.5),
            skill_level=data.get("skill_level", 0.5),
            base_sp_pool=data.get("base_sp_pool", 1.0),
            sp_drain_resistance=data.get("sp_drain_resistance", 1.0),
            team_name=data.get("team_name"),
            car_color=tuple(data.get("car_color", [128, 128, 128])),
            headlight_color=tuple(data.get("headlight_color", [255, 255, 200])),
            zones=data.get("zones", []),
            unlock_requirements=data.get("unlock_requirements", {}),
        )
        
        # Restore stats if present
        if "stats" in data:
            stats_data = data["stats"]
            rival.stats = RivalStats(
                battles_fought=stats_data.get("battles_fought", 0),
                battles_won=stats_data.get("battles_won", 0),
                battles_lost=stats_data.get("battles_lost", 0),
                total_sp_drained=stats_data.get("total_sp_drained", 0.0),
                total_sp_lost=stats_data.get("total_sp_lost", 0.0),
                best_victory_time_s=stats_data.get("best_victory_time_s"),
            )
        
        return rival
    
    def compute_entity_hash(self) -> str:
        """Compute hash for SSOT verification."""
        data = {
            "rival_id": self.rival_id,
            "tier": self.tier.name,
            "base_sp_pool": self.base_sp_pool,
            "aggression": self.aggression,
        }
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]


# Factory functions for creating standard rivals
def create_wanderer(
    name: str,
    car_class: str,
    zones: list,
    **kwargs
) -> RivalEntity:
    """Create a wanderer-tier rival."""
    return RivalEntity(
        rival_id=f"wanderer_{uuid.uuid4().hex[:8]}",
        name=name,
        tier=RivalTier.WANDERER,
        car_class=car_class,
        zones=zones,
        base_sp_pool=0.8,
        aggression=0.3 + kwargs.get("aggression_bonus", 0),
        skill_level=0.3 + kwargs.get("skill_bonus", 0),
        **kwargs,
    )


def create_boss(
    name: str,
    car_class: str,
    team_name: str,
    zones: list,
    **kwargs
) -> RivalEntity:
    """Create a boss-tier rival."""
    return RivalEntity(
        rival_id=f"boss_{uuid.uuid4().hex[:8]}",
        name=name,
        tier=RivalTier.BOSS,
        car_class=car_class,
        team_name=team_name,
        zones=zones,
        base_sp_pool=1.2,
        aggression=0.6 + kwargs.get("aggression_bonus", 0),
        skill_level=0.6 + kwargs.get("skill_bonus", 0),
        **kwargs,
    )


def create_team_leader(
    name: str,
    car_class: str,
    team_name: str,
    **kwargs
) -> RivalEntity:
    """Create a team leader rival (ultimate challenge)."""
    return RivalEntity(
        rival_id=f"leader_{uuid.uuid4().hex[:8]}",
        name=name,
        tier=RivalTier.TEAM_LEADER,
        car_class=car_class,
        team_name=team_name,
        zones=[],  # Team leaders spawn anywhere
        base_sp_pool=1.5,
        sp_drain_resistance=0.8,  # Takes less damage
        aggression=0.9,
        skill_level=0.9,
        **kwargs,
    )


# Standalone test
if __name__ == "__main__":
    print("🏎️  Rival Entity Test\n")
    
    # Create sample rivals
    wanderer = create_wanderer(
        name="Night Drifter",
        car_class="S13",
        zones=["hatzenbach", "flugplatz"],
        car_color=(64, 64, 64),
    )
    
    boss = create_boss(
        name="Karussell King",
        car_class="GT-R",
        team_name="Ring Masters",
        zones=["karussell"],
        car_color=(255, 0, 0),
    )
    
    leader = create_team_leader(
        name="Shadow Ace",
        car_class="R34 GT-R",
        team_name="Midnight Runners",
        car_color=(0, 0, 0),
        headlight_color=(255, 200, 0),
    )
    
    for rival in [wanderer, boss, leader]:
        print(f"  {rival.tier_name}: {rival.display_name}")
        print(f"    Car: {rival.car_class} | SP Pool: {rival.base_sp_pool}")
        print(f"    Aggression: {rival.aggression:.1f} | Skill: {rival.skill_level:.1f}")
        print(f"    Entity Hash: {rival.compute_entity_hash()}")
        print()
    
    # Test battle simulation
    print("📊 Simulating battle result recording...")
    boss.record_battle_result(won=False, duration_s=45.2, sp_drained=0.8, sp_lost=1.0)
    boss.record_battle_result(won=True, duration_s=38.5, sp_drained=1.0, sp_lost=0.3)
    print(f"  {boss.name} stats: {boss.stats.to_dict()}")
