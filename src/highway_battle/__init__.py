"""
Highway Battle Game Kernel
Tokyo Extreme Racer-style highway racing game mechanics.

Core Components:
- SPSystem: Spirit Points battle mechanics
- RivalEntity: AI-controlled opponent cars
- BattleManager: 1v1 duel orchestration
- RivalSpawner: Zone-based encounter spawning
- HeadlightFlash: Challenge initiation system
"""

from .sp_system import SPSystem, SPConfig
from .rival_entity import RivalEntity, RivalTier
from .battle_manager import BattleManager, BattleState, BattleResult
from .rival_spawner import RivalSpawner, SpawnZone
from .headlight_flash import HeadlightFlashSystem, FlashChallenge

__all__ = [
    "SPSystem",
    "SPConfig",
    "RivalEntity",
    "RivalTier",
    "BattleManager",
    "BattleState",
    "BattleResult",
    "RivalSpawner",
    "SpawnZone",
    "HeadlightFlashSystem",
    "FlashChallenge",
]

__version__ = "0.1.0"
