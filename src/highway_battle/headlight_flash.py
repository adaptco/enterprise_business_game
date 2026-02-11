"""
Headlight Flash System - Battle initiation mechanic.

The classic Tokyo Extreme Racer challenge system:
1. Player flashes headlights when behind a rival
2. Rival accepts (or auto-accepts within range)
3. Battle begins after countdown

This creates the iconic "flash to challenge" experience.
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timezone

from .rival_entity import RivalEntity
from .battle_manager import BattleManager, BattleState


@dataclass
class FlashChallenge:
    """Pending headlight flash challenge."""
    
    challenger_id: str  # Usually "player"
    target: RivalEntity
    issued_tick: int
    accept_deadline_tick: int
    accepted: bool = False
    declined: bool = False
    
    def is_expired(self, current_tick: int) -> bool:
        """Check if challenge window has expired."""
        return current_tick > self.accept_deadline_tick
    
    def to_dict(self) -> dict:
        return {
            "challenger_id": self.challenger_id,
            "target_id": self.target.rival_id,
            "target_name": self.target.name,
            "issued_tick": self.issued_tick,
            "accept_deadline_tick": self.accept_deadline_tick,
            "accepted": self.accepted,
            "declined": self.declined,
        }


class HeadlightFlashSystem:
    """
    Manages the 'flash headlights to challenge' mechanic.
    
    Usage:
        flash_system = HeadlightFlashSystem(battle_manager)
        
        # Player flashes at rival
        challenge = flash_system.issue_challenge(
            player_progress_m=1500.0,
            rival=spotted_rival,
            rival_progress_m=1520.0,
            current_tick=1000
        )
        
        if challenge:
            # Rival can accept within window
            battle = flash_system.accept_challenge(challenge, current_tick=1050)
    """
    
    def __init__(
        self,
        battle_manager: BattleManager,
        flash_range_m: float=75.0,
        response_window_ticks: int=180,  # 3 seconds at 60Hz
        auto_accept_range_m: float=30.0,
    ):
        self.battle_manager = battle_manager
        self.flash_range_m = flash_range_m
        self.response_window_ticks = response_window_ticks
        self.auto_accept_range_m = auto_accept_range_m
        
        self.pending_challenge: Optional[FlashChallenge] = None
        self.flash_cooldown_ticks = 60  # 1 second cooldown
        self.last_flash_tick = -9999
    
    def can_flash(self, current_tick: int) -> bool:
        """Check if player can flash headlights."""
        return (current_tick - self.last_flash_tick) >= self.flash_cooldown_ticks
    
    def issue_challenge(
        self,
        player_progress_m: float,
        rival: RivalEntity,
        rival_progress_m: float,
        current_tick: int,
    ) -> Optional[FlashChallenge]:
        """
        Issue a headlight flash challenge to a rival.
        
        Args:
            player_progress_m: Player's current track progress
            rival: Target rival to challenge
            rival_progress_m: Rival's current track progress
            current_tick: Current simulation tick
            
        Returns:
            FlashChallenge if valid, None if out of range or on cooldown
        """
        if not self.can_flash(current_tick):
            return None
        
        # Check range (must be behind and within flash range)
        gap = rival_progress_m - player_progress_m
        if gap < 0 or gap > self.flash_range_m:
            return None
        
        self.last_flash_tick = current_tick
        
        challenge = FlashChallenge(
            challenger_id="player",
            target=rival,
            issued_tick=current_tick,
            accept_deadline_tick=current_tick + self.response_window_ticks,
        )
        
        # Auto-accept if very close
        if gap <= self.auto_accept_range_m:
            challenge.accepted = True
        
        self.pending_challenge = challenge
        return challenge
    
    def tick(self, current_tick: int) -> Optional[BattleState]:
        """
        Process pending challenge each tick.
        
        Returns:
            BattleState if challenge was accepted and battle started
        """
        if not self.pending_challenge:
            return None
        
        challenge = self.pending_challenge
        
        # Check expiration
        if challenge.is_expired(current_tick):
            self.pending_challenge = None
            return None
        
        # If accepted, start battle
        if challenge.accepted:
            self.pending_challenge = None
            return self.battle_manager.initiate_battle(
                rival=challenge.target,
                current_tick=current_tick,
            )
        
        return None
    
    def accept_challenge(self, current_tick: int) -> Optional[BattleState]:
        """
        Accept the pending challenge (called by rival AI or player prompt).
        
        Returns:
            BattleState if battle started
        """
        if not self.pending_challenge:
            return None
        
        if self.pending_challenge.is_expired(current_tick):
            self.pending_challenge = None
            return None
        
        self.pending_challenge.accepted = True
        return self.tick(current_tick)
    
    def decline_challenge(self):
        """Decline the pending challenge."""
        if self.pending_challenge:
            self.pending_challenge.declined = True
            self.pending_challenge = None
    
    def get_pending_challenge(self) -> Optional[FlashChallenge]:
        """Get currently pending challenge."""
        return self.pending_challenge


# Standalone test
if __name__ == "__main__":
    from .rival_entity import create_wanderer
    from .battle_manager import BattleManager
    from .sp_system import SPConfig
    
    print("🏎️  Headlight Flash System Test\n")
    
    # Setup
    manager = BattleManager(SPConfig())
    flash_system = HeadlightFlashSystem(manager)
    
    rival = create_wanderer("Night Drifter", "S13", ["hatzenbach"])
    
    # Test challenge
    print("  Player flashes headlights...")
    challenge = flash_system.issue_challenge(
        player_progress_m=1000.0,
        rival=rival,
        rival_progress_m=1030.0,  # 30m ahead
        current_tick=100,
    )
    
    if challenge:
        print(f"  Challenge issued to: {challenge.target.name}")
        print(f"  Auto-accepted: {challenge.accepted}")
        print(f"  Window expires at tick: {challenge.accept_deadline_tick}")
        
        # Process
        battle = flash_system.tick(101)
        if battle:
            print(f"\n  Battle started! ID: {battle.battle_id}")
    
    # Test out of range
    print("\n  Testing out of range flash...")
    challenge2 = flash_system.issue_challenge(
        player_progress_m=1000.0,
        rival=rival,
        rival_progress_m=1200.0,  # 200m ahead (too far)
        current_tick=200,
    )
    print(f"  Challenge result: {challenge2}")  # Should be None
