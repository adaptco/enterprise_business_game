"""
Rival Spawner - Zone-based encounter spawning system.

Manages where and when rivals appear on the highway:
- Zone-based spawn locations
- Spawn probability based on player progress
- Rival pool management
- Progressive difficulty scaling
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
import random
import json

from .rival_entity import RivalEntity, RivalTier


@dataclass
class SpawnZone:
    """Highway zone where rivals can spawn."""
    
    zone_id: str
    zone_name: str
    track_start_m: float
    track_end_m: float
    spawn_chance_per_tick: float = 0.001
    
    # Rival pools by tier
    wanderer_pool: List[str] = field(default_factory=list)  # Rival IDs
    boss_pool: List[str] = field(default_factory=list)
    
    # Cooldown (prevents spawn spam)
    cooldown_ticks: int = 600  # 10 seconds at 60Hz
    last_spawn_tick: int = -9999
    
    def is_player_in_zone(self, player_progress_m: float) -> bool:
        """Check if player is currently in this zone."""
        return self.track_start_m <= player_progress_m < self.track_end_m
    
    def is_on_cooldown(self, current_tick: int) -> bool:
        """Check if zone is on spawn cooldown."""
        return (current_tick - self.last_spawn_tick) < self.cooldown_ticks
    
    def to_dict(self) -> dict:
        return {
            "zone_id": self.zone_id,
            "zone_name": self.zone_name,
            "track_start_m": self.track_start_m,
            "track_end_m": self.track_end_m,
            "spawn_chance_per_tick": self.spawn_chance_per_tick,
            "wanderer_pool": self.wanderer_pool,
            "boss_pool": self.boss_pool,
            "cooldown_ticks": self.cooldown_ticks,
        }


class RivalSpawner:
    """
    Manages rival spawning on the highway.
    
    Usage:
        spawner = RivalSpawner(zones, rivals)
        
        for tick in simulation_loop:
            spawned = spawner.tick(
                player_progress_m=1500.0,
                current_tick=tick,
                rng=random.Random(42)
            )
            
            if spawned:
                print(f"Rival spotted: {spawned.name}")
    """
    
    def __init__(
        self,
        zones: List[SpawnZone]=None,
        rivals: Dict[str, RivalEntity]=None,
    ):
        self.zones = zones or []
        self.rivals = rivals or {}
        self.active_rivals: List[RivalEntity] = []
        self.max_active_rivals = 1  # Only one at a time for now
        
        # Stats
        self.total_spawns = 0
        self.spawns_by_zone: Dict[str, int] = {}
    
    def add_zone(self, zone: SpawnZone):
        """Add a spawn zone."""
        self.zones.append(zone)
        self.spawns_by_zone[zone.zone_id] = 0
    
    def register_rival(self, rival: RivalEntity):
        """Register a rival for spawning."""
        self.rivals[rival.rival_id] = rival
    
    def tick(
        self,
        player_progress_m: float,
        current_tick: int,
        rng: random.Random,
    ) -> Optional[RivalEntity]:
        """
        Check for rival spawn this tick.
        
        Args:
            player_progress_m: Player's current track progress
            current_tick: Current simulation tick
            rng: Random number generator (for determinism)
            
        Returns:
            Spawned RivalEntity or None
        """
        # Don't spawn if at max active rivals
        if len(self.active_rivals) >= self.max_active_rivals:
            return None
        
        # Find zones player is in
        active_zones = [z for z in self.zones if z.is_player_in_zone(player_progress_m)]
        
        for zone in active_zones:
            # Check cooldown
            if zone.is_on_cooldown(current_tick):
                continue
            
            # Roll for spawn
            if rng.random() < zone.spawn_chance_per_tick:
                rival = self._select_rival_for_zone(zone, rng)
                if rival:
                    zone.last_spawn_tick = current_tick
                    self.active_rivals.append(rival)
                    self.total_spawns += 1
                    self.spawns_by_zone[zone.zone_id] = self.spawns_by_zone.get(zone.zone_id, 0) + 1
                    return rival
        
        return None
    
    def _select_rival_for_zone(
        self,
        zone: SpawnZone,
        rng: random.Random,
    ) -> Optional[RivalEntity]:
        """Select a rival to spawn from zone's pool."""
        # Combine pools with weighting (wanderers more common)
        candidates = []
        
        for rival_id in zone.wanderer_pool:
            if rival_id in self.rivals:
                candidates.append((self.rivals[rival_id], 3))  # Weight 3
        
        for rival_id in zone.boss_pool:
            if rival_id in self.rivals:
                candidates.append((self.rivals[rival_id], 1))  # Weight 1
        
        if not candidates:
            return None
        
        # Weighted random selection
        total_weight = sum(w for _, w in candidates)
        roll = rng.random() * total_weight
        
        cumulative = 0
        for rival, weight in candidates:
            cumulative += weight
            if roll < cumulative:
                return rival
        
        return candidates[-1][0]  # Fallback
    
    def remove_active_rival(self, rival_id: str):
        """Remove a rival from active list (after battle ends)."""
        self.active_rivals = [r for r in self.active_rivals if r.rival_id != rival_id]
    
    def get_active_rivals(self) -> List[RivalEntity]:
        """Get currently active (visible) rivals."""
        return self.active_rivals.copy()
    
    def get_stats(self) -> dict:
        """Get spawner statistics."""
        return {
            "total_spawns": self.total_spawns,
            "spawns_by_zone": self.spawns_by_zone,
            "active_rivals": len(self.active_rivals),
            "registered_rivals": len(self.rivals),
            "zones": len(self.zones),
        }


def create_nurburgring_zones() -> List[SpawnZone]:
    """Create spawn zones for Nürburgring Nordschleife."""
    return [
        SpawnZone(
            zone_id="hatzenbach",
            zone_name="Hatzenbach",
            track_start_m=0,
            track_end_m=1200,
            spawn_chance_per_tick=0.002,
        ),
        SpawnZone(
            zone_id="flugplatz",
            zone_name="Flugplatz",
            track_start_m=1200,
            track_end_m=2500,
            spawn_chance_per_tick=0.0015,
        ),
        SpawnZone(
            zone_id="aremberg",
            zone_name="Aremberg",
            track_start_m=2500,
            track_end_m=3800,
            spawn_chance_per_tick=0.001,
        ),
        SpawnZone(
            zone_id="fuchsrohre",
            zone_name="Fuchsröhre",
            track_start_m=3800,
            track_end_m=5500,
            spawn_chance_per_tick=0.002,
        ),
        SpawnZone(
            zone_id="adenauer_forst",
            zone_name="Adenauer Forst",
            track_start_m=5500,
            track_end_m=7200,
            spawn_chance_per_tick=0.001,
        ),
        SpawnZone(
            zone_id="karussell",
            zone_name="Karussell",
            track_start_m=7200,
            track_end_m=9500,
            spawn_chance_per_tick=0.0015,
        ),
        SpawnZone(
            zone_id="pflanzgarten",
            zone_name="Pflanzgarten",
            track_start_m=9500,
            track_end_m=12000,
            spawn_chance_per_tick=0.002,
        ),
        SpawnZone(
            zone_id="schwalbenschwanz",
            zone_name="Schwalbenschwanz",
            track_start_m=12000,
            track_end_m=14500,
            spawn_chance_per_tick=0.0015,
        ),
        SpawnZone(
            zone_id="dottinger_hohe",
            zone_name="Döttinger Höhe",
            track_start_m=14500,
            track_end_m=18500,
            spawn_chance_per_tick=0.003,  # Higher on straight
        ),
        SpawnZone(
            zone_id="antoniusbuche",
            zone_name="Antoniusbuche",
            track_start_m=18500,
            track_end_m=20800,
            spawn_chance_per_tick=0.001,
        ),
    ]


# Standalone test
if __name__ == "__main__":
    from .rival_entity import create_wanderer, create_boss
    
    print("🏎️  Rival Spawner Test\n")
    
    # Create zones
    zones = create_nurburgring_zones()
    print(f"  Created {len(zones)} spawn zones")
    
    # Create some rivals
    rivals = [
        create_wanderer("Night Drifter", "S13", ["hatzenbach", "flugplatz"]),
        create_wanderer("Speed Demon", "RX-7", ["flugplatz", "fuchsrohre"]),
        create_boss("Karussell King", "GT-R", "Ring Masters", ["karussell"]),
    ]
    
    # Set up spawner
    spawner = RivalSpawner(zones)
    for rival in rivals:
        spawner.register_rival(rival)
        # Add to zone pools
        for zone in zones:
            if zone.zone_id in rival.zones:
                if rival.tier == RivalTier.WANDERER:
                    zone.wanderer_pool.append(rival.rival_id)
                else:
                    zone.boss_pool.append(rival.rival_id)
    
    print(f"  Registered {len(rivals)} rivals")
    
    # Simulate driving through track
    print("\n  Simulating lap...")
    rng = random.Random(42)
    spawns = []
    
    for tick in range(12000):  # ~3 minutes at 60Hz
        # Player progresses through track
        player_progress = (tick * 0.8) % 20800  # ~48 m/s looping
        
        spawned = spawner.tick(player_progress, tick, rng)
        if spawned:
            spawns.append((tick, player_progress, spawned.name))
            # Remove after "battle" for testing
            spawner.remove_active_rival(spawned.rival_id)
    
    print(f"\n  Spawns during lap:")
    for tick, progress, name in spawns[:10]:  # Show first 10
        print(f"    t={tick/60:.1f}s @ {progress:.0f}m: {name}")
    
    if len(spawns) > 10:
        print(f"    ... and {len(spawns) - 10} more")
    
    print(f"\n  📊 Spawner stats: {spawner.get_stats()}")
