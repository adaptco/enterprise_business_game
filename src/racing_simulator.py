"""
Nürburgring AI Racing Simulator
Deterministic racing simulator with IPFS checkpoint integration.
"""

import numpy as np
import hashlib
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from enum import Enum


class TrackSection(Enum):
    """Major sections of Nürburgring Nordschleife"""
    HATZENBACH = "hatzenbach"
    FLUGPLATZ = "flugplatz"
    AREMBERG = "aremberg"
    FUCHSROHRE = "fuchsrohre"
    ADENAUER_FORST = "adenauer_forst"
    KARUSSELL = "karussell"
    PFLANZGARTEN = "pflanzgarten"
    SCHWALBENSCHWANZ = "schwalbenschwanz"
    DOTTINGER_HOHE = "dottinger_hohe"
    ANTONIUSBUCHE = "antoniusbuche"


class TireCompound(Enum):
    """Tire compound types with different wear/grip characteristics"""
    SOFT = "soft"  # High grip, fast degradation
    MEDIUM = "medium"  # Balanced
    HARD = "hard"  # Low grip, slow degradation


@dataclass
class TireState:
    """Tire degradation state per wheel"""
    compound: TireCompound = TireCompound.MEDIUM
    wear: float = 0.0  # 0.0 (fresh) to 1.0 (worn out)
    temperature: float = 80.0  # degrees C (optimal: 80-100)
    
    @property
    def grip_multiplier(self) -> float:
        """Grip based on compound, wear, and temperature."""
        # Compound base grip
        compound_grip = {
            TireCompound.SOFT: 1.15,
            TireCompound.MEDIUM: 1.0,
            TireCompound.HARD: 0.90
        }[self.compound]
        
        # Wear degradation (non-linear: accelerates after 50%)
        wear_factor = max(0.3, 1.0 - (self.wear ** 1.5))
        
        # Temperature factor (optimal 80-100C)
        if 80 <= self.temperature <= 100:
            temp_factor = 1.0
        elif self.temperature < 80:
            temp_factor = 0.7 + 0.3 * (self.temperature / 80)
        else:
            temp_factor = max(0.6, 1.0 - 0.01 * (self.temperature - 100))
        
        return compound_grip * wear_factor * temp_factor
    
    @property
    def wear_rate_multiplier(self) -> float:
        """How fast this compound wears."""
        return {
            TireCompound.SOFT: 1.5,  # 50% faster wear
            TireCompound.MEDIUM: 1.0,
            TireCompound.HARD: 0.6  # 40% slower wear
        }[self.compound]


@dataclass
class FuelState:
    """Fuel tank state"""
    current_kg: float = 110.0  # Current fuel load
    max_kg: float = 110.0  # Tank capacity
    consumption_rate: float = 2.5  # kg per lap (approx)
    
    @property
    def mass_penalty(self) -> float:
        """Lap time penalty from fuel weight (0-2%)."""
        return (self.current_kg / self.max_kg) * 0.02
    
    @property
    def normalized(self) -> float:
        """Fuel level 0-1."""
        return self.current_kg / self.max_kg


@dataclass
class WeatherState:
    """Dynamic weather affecting track grip"""
    grip_mu: float = 1.2  # Surface friction (dry=1.2, wet=0.6)
    rain_intensity: float = 0.0  # 0.0 (dry) to 1.0 (heavy rain)
    transition_prob: float = 0.001  # Probability of weather change per tick
    drying_rate: float = 0.0005  # How fast track dries after rain stops
    
    def tick(self, rng: np.random.RandomState) -> None:
        """Update weather state (called each simulation tick)."""
        # Random weather transition
        if rng.rand() < self.transition_prob:
            if self.rain_intensity == 0:
                # Start raining
                self.rain_intensity = rng.uniform(0.2, 0.8)
            else:
                # Stop raining
                self.rain_intensity = 0.0
        
        # Update grip based on rain
        if self.rain_intensity > 0:
            # Wet track - grip decreases
            target_grip = 0.6 + 0.3 * (1 - self.rain_intensity)
            self.grip_mu = max(target_grip, self.grip_mu - 0.02)
        else:
            # Drying track
            self.grip_mu = min(1.2, self.grip_mu + self.drying_rate)


@dataclass
class VehicleState:
    """Complete vehicle dynamics state (deterministic)"""
    # Kinematics
    speed: float  # m/s
    yaw_rate: float  # rad/s
    longitudinal_accel: float  # m/s^2
    lateral_accel: float  # m/s^2
    
    # Control inputs
    steering_angle: float  # rad
    throttle_input: float  # 0.0-1.0
    brake_input: float  # 0.0-1.0
    
    # Powertrain
    engine_rpm: int
    gear: int
    
    # Wheels (FL, FR, RL, RR)
    wheel_speeds: Tuple[float, float, float, float]  # rad/s
    tire_slip_ratios: Tuple[float, float, float, float]
    suspension_travel: Tuple[float, float, float, float]  # m
    
    # Position & navigation
    track_x: float  # m
    track_y: float  # m
    heading: float  # rad
    distance_to_centerline: float  # m
    track_progress: float  # 0.0-1.0
    
    # Track geometry
    current_curvature: float  # 1/m
    upcoming_curvature: Tuple[float, float, float, float, float]  # +10m, +25m, +50m, +100m, +200m
    track_gradient: float  # rad
    distance_to_apex: float  # m
    apex_radius: float  # m
    
    # Environmental sensors (raycast distances)
    dist_left_edge: float  # m
    dist_right_edge: float  # m
    front_ray: float  # m
    front_left_ray: float  # m
    front_right_ray: float  # m
    
    # Metadata (must come before default fields)
    current_section: TrackSection
    timestamp: float  # simulation time
    tick: int
    
    # Degradation state (new fields with defaults for backwards compat)
    tire_wear: float = 0.0  # Average tire wear 0.0-1.0
    tire_grip_mult: float = 1.0  # Current tire grip multiplier
    fuel_remaining: float = 110.0  # Fuel in kg
    fuel_normalized: float = 1.0  # Fuel level 0.0-1.0
    weather_grip: float = 1.2  # Track grip from weather
    rain_intensity: float = 0.0  # Current rain 0.0-1.0


@dataclass
class ControlInput:
    """AI control output"""
    steering_command: float  # -1.0 to 1.0
    throttle_command: float  # 0.0 to 1.0
    brake_command: float  # 0.0 to 1.0


class NurburgringTrack:
    """
    Nürburgring Nordschleife track geometry.
    Simplified representation for deterministic simulation.
    """
    
    TRACK_LENGTH = 20830.0  # meters
    
    def __init__(self, seed: int=42):
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        
        # Define track sections with approximate distances
        self.sections = {
            TrackSection.HATZENBACH: (0, 1200),
            TrackSection.FLUGPLATZ: (1200, 2500),
            TrackSection.AREMBERG: (2500, 3800),
            TrackSection.FUCHSROHRE: (3800, 5500),
            TrackSection.ADENAUER_FORST: (5500, 7200),
            TrackSection.KARUSSELL: (7200, 9500),
            TrackSection.PFLANZGARTEN: (9500, 12000),
            TrackSection.SCHWALBENSCHWANZ: (12000, 14500),
            TrackSection.DOTTINGER_HOHE: (14500, 18500),
            TrackSection.ANTONIUSBUCHE: (18500, 20830)
        }
        
        # Generate deterministic curvature profile
        self._generate_track_geometry()
    
    def _generate_track_geometry(self):
        """Generate deterministic track curvature and elevation."""
        # Sample points along track
        self.num_points = 2083  # 10m resolution
        self.sample_distances = np.linspace(0, self.TRACK_LENGTH, self.num_points)
        
        # Curvature profile (simplified sinusoidal + noise for corners)
        base_curvature = 0.001 * np.sin(2 * np.pi * self.sample_distances / 5000.0)
        
        # Add sharp corners at known sections
        corner_curvatures = np.zeros(self.num_points)
        corner_positions = [1800, 3200, 5800, 7500, 10200, 13000, 15500, 19200]  # Approximate
        for pos in corner_positions:
            idx = int(pos / 10)
            if idx < self.num_points:
                corner_curvatures[idx - 5:idx + 5] = 0.05 * np.exp(-0.5 * ((np.arange(10) - 4.5) / 2) ** 2)
        
        self.curvature_profile = base_curvature + corner_curvatures
        
        # Elevation profile (simplified)
        self.elevation_profile = 50 * np.sin(2 * np.pi * self.sample_distances / 8000.0) + \
                                 100 * np.sin(2 * np.pi * self.sample_distances / 20830.0)
        
        # Gradient
        self.gradient_profile = np.gradient(self.elevation_profile, 10.0)  # 10m spacing
    
    def get_track_data(self, progress: float) -> Dict[str, Any]:
        """
        Get track data at given progress (0.0-1.0).
        
        Returns:
            curvature, gradient, upcoming_curvature, section
        """
        distance = progress * self.TRACK_LENGTH
        idx = int((distance / self.TRACK_LENGTH) * self.num_points)
        idx = min(idx, self.num_points - 1)
        
        # Current values
        curvature = self.curvature_profile[idx]
        gradient = self.gradient_profile[idx]
        
        # Upcoming curvature horizon
        horizon_distances = [10, 25, 50, 100, 200]
        upcoming_curvature = []
        for d in horizon_distances:
            future_idx = idx + int(d / 10)
            future_idx = min(future_idx, self.num_points - 1)
            upcoming_curvature.append(self.curvature_profile[future_idx])
        
        # Determine section
        section = TrackSection.HATZENBACH
        for sec, (start, end) in self.sections.items():
            if start <= distance < end:
                section = sec
                break
        
        return {
            'curvature': curvature,
            'gradient': gradient,
            'upcoming_curvature': tuple(upcoming_curvature),
            'section': section
        }


class DeterministicVehiclePhysics:
    """
    Simplified deterministic vehicle physics.
    Fixed-step integration for replay consistency.
    Now includes tire wear, fuel consumption, and weather effects.
    """
    
    DT = 0.016666  # 60 Hz timestep
    
    def __init__(self, seed: int=42, tire_compound: TireCompound=TireCompound.MEDIUM):
        self.seed = seed
        self.initial_tire_compound = tire_compound
        self.reset()
    
    def reset(self, tire_compound: Optional[TireCompound]=None):
        """Reset to initial state."""
        self.position = np.array([0.0, 0.0])  # [x, y]
        self.velocity = 0.0  # m/s
        self.heading = 0.0  # rad
        self.yaw_rate = 0.0  # rad/s
        self.wheel_speeds = np.array([0.0, 0.0, 0.0, 0.0])
        self.engine_rpm = 1000
        self.gear = 1
        
        # Tire state (new)
        compound = tire_compound or self.initial_tire_compound
        self.tire_state = TireState(compound=compound, wear=0.0, temperature=60.0)
        
        # Fuel state (new)
        self.fuel_state = FuelState(current_kg=110.0, max_kg=110.0)
    
    def pit_stop(self, new_compound: TireCompound=TireCompound.MEDIUM, fuel_kg: float=110.0):
        """Perform pit stop: replace tires and refuel."""
        self.tire_state = TireState(compound=new_compound, wear=0.0, temperature=60.0)
        self.fuel_state.current_kg = min(fuel_kg, self.fuel_state.max_kg)
    
    def step(
        self,
        control: ControlInput,
        track_curvature: float,
        track_gradient: float,
        weather: Optional[WeatherState]=None
    ) -> Tuple[float, float, float]:
        """
        Advance physics by one timestep.
        Deterministic integration using fixed timestep.
        
        Returns:
            (longitudinal_accel, lateral_accel, steering_angle)
        """
        # Get effective grip from tire and weather
        tire_grip = self.tire_state.grip_multiplier
        weather_grip = weather.grip_mu if weather else 1.2
        effective_grip = tire_grip * (weather_grip / 1.2)  # Normalize weather grip
        
        # Mass penalty from fuel
        mass_penalty = self.fuel_state.mass_penalty  # 0-2%
        
        # Simplified longitudinal dynamics with grip and mass effects
        max_accel = 10.0 * effective_grip * (1 - mass_penalty)  # m/s^2
        max_brake = 15.0 * effective_grip  # m/s^2
        
        accel = control.throttle_command * max_accel - control.brake_command * max_brake
        
        # Apply gradient effect
        gravity_component = -9.81 * np.sin(track_gradient)
        accel += gravity_component
        
        # Update velocity
        self.velocity += accel * self.DT
        self.velocity = max(0.0, self.velocity)  # No reverse
        
        # Lateral dynamics with grip limit
        max_steering = 0.52 * effective_grip  # rad (~30 degrees at full grip)
        steering_angle = control.steering_command * max_steering
        
        # Yaw rate from bicycle model
        wheelbase = 2.7  # m
        self.yaw_rate = (self.velocity / wheelbase) * np.tan(steering_angle)
        
        # Update heading
        self.heading += self.yaw_rate * self.DT
        self.heading = self.heading % (2 * np.pi)
        
        # Update position (simple integration)
        dx = self.velocity * np.cos(self.heading) * self.DT
        dy = self.velocity * np.sin(self.heading) * self.DT
        self.position += np.array([dx, dy])
        
        # Update wheel speeds (simplified)
        self.wheel_speeds = np.ones(4) * (self.velocity / 0.33)  # 0.33m wheel radius
        
        # Update engine RPM (simplified)
        gear_ratios = [3.5, 2.5, 1.8, 1.3, 1.0, 0.8]
        if self.gear < len(gear_ratios):
            self.engine_rpm = int(self.wheel_speeds[0] * gear_ratios[self.gear - 1] * 60 / (2 * np.pi))
        
        # Auto shift (simple logic)
        if self.engine_rpm > 7000 and self.gear < 6:
            self.gear += 1
        elif self.engine_rpm < 3000 and self.gear > 1:
            self.gear -= 1
        
        # === TIRE DEGRADATION ===
        # Wear increases with throttle/brake usage and speed
        throttle_wear = 0.0015 * (control.throttle_command ** 2)
        brake_wear = 0.001 * (control.brake_command ** 2)
        speed_wear = 0.0001 * (self.velocity / 80.0)  # Faster = more wear
        base_wear = (throttle_wear + brake_wear + speed_wear) * self.tire_state.wear_rate_multiplier
        self.tire_state.wear = min(1.0, self.tire_state.wear + base_wear)
        
        # Tire temperature (heats up with speed/aggression, cools when slow)
        heat_rate = 0.5 * (control.throttle_command + control.brake_command + abs(control.steering_command))
        cool_rate = 0.2 * (1 - self.velocity / 100)
        self.tire_state.temperature += (heat_rate - cool_rate) * self.DT * 10
        self.tire_state.temperature = np.clip(self.tire_state.temperature, 20.0, 130.0)
        
        # === FUEL CONSUMPTION ===
        # Burn rate: ~2.5 kg/lap at ~6min lap = ~0.007 kg/s at racing speed
        fuel_burn = 0.007 * (0.5 + 0.5 * control.throttle_command) * self.DT * 60
        self.fuel_state.current_kg = max(0.0, self.fuel_state.current_kg - fuel_burn)
        
        # Compute accelerations
        long_accel = accel
        lat_accel = self.velocity * self.yaw_rate
        
        return long_accel, lat_accel, steering_angle


class RacingSimulator:
    """
    Main racing simulator with checkpoint integration.
    Now includes tire wear, fuel consumption, and dynamic weather.
    """
    
    def __init__(
        self,
        seed: int=42,
        ipfs_bridge=None,
        tire_compound: TireCompound=TireCompound.MEDIUM,
        enable_weather: bool=True
    ):
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        self.ipfs_bridge = ipfs_bridge
        
        # Initialize components
        self.track = NurburgringTrack(seed)
        self.physics = DeterministicVehiclePhysics(seed, tire_compound)
        
        # Weather system (new)
        self.weather = WeatherState() if enable_weather else None
        self.enable_weather = enable_weather
        
        # Simulation state
        self.tick = 0
        self.start_time = datetime.now(timezone.utc)
        self.current_lap = 0
        self.track_progress = 0.0
        
        # Pit stop state (new)
        self.pit_time_penalty = 25.0  # seconds (realistic F1 pit time)
        self.pit_remaining_time = 0.0  # Remaining time in pit
        self.in_pit = False
        self._pit_compound = TireCompound.MEDIUM
        self._pit_fuel = 110.0
        
        # State history for training
        self.state_action_history: List[Dict[str, Any]] = []
    
    def pit_stop(self, new_compound: TireCompound=TireCompound.MEDIUM, fuel_kg: float=110.0):
        """Perform pit stop: replace tires and refuel (instant)."""
        self.physics.pit_stop(new_compound, fuel_kg)
        print(f"🔧 Pit stop: {new_compound.value} tires, {fuel_kg:.1f}kg fuel")
    
    def trigger_pit_entry(self, new_compound: TireCompound=TireCompound.MEDIUM, fuel_kg: float=110.0):
        """Enter pit lane - starts time penalty countdown."""
        if not self.in_pit:
            self.in_pit = True
            self.pit_remaining_time = self.pit_time_penalty
            self._pit_compound = new_compound
            self._pit_fuel = fuel_kg
            self.physics.velocity = 0.0  # Stop car
            print(f"🚦 Entering pit: {self.pit_time_penalty}s penalty")
    
    def _process_pit_time(self) -> bool:
        """Process pit stop time. Returns True if still in pit."""
        if not self.in_pit:
            return False
        
        self.pit_remaining_time -= self.physics.DT
        
        if self.pit_remaining_time <= 0:
            # Pit complete - apply tire/fuel changes
            self.physics.pit_stop(self._pit_compound, self._pit_fuel)
            self.in_pit = False
            self.pit_remaining_time = 0.0
            print(f"✅ Pit complete: {self._pit_compound.value} tires, {self._pit_fuel:.1f}kg fuel")
            return False
        
        return True  # Still in pit
    
    @staticmethod
    def pit_urgency(tire_wear: float, fuel_kg: float) -> float:
        """Heuristic for RL: pit urgency signal based on wear and fuel."""
        fuel_normalized = fuel_kg / 110.0
        return min(1.0, (tire_wear * 0.8 + (1 - fuel_normalized) * 0.6))
    
    def get_current_state(self, track_data: Dict) -> VehicleState:
        """Build complete vehicle state."""
        # Raycast distances (simplified - assume track width = 12m)
        track_width = 12.0
        dist_left = track_width / 2 + self.physics.position[1]
        dist_right = track_width / 2 - self.physics.position[1]
        
        return VehicleState(
            speed=self.physics.velocity,
            yaw_rate=self.physics.yaw_rate,
            longitudinal_accel=0.0,  # Updated in step
            lateral_accel=0.0,  # Updated in step
            steering_angle=0.0,  # Updated in step
            throttle_input=0.0,  # Updated in step
            brake_input=0.0,  # Updated in step
            engine_rpm=self.physics.engine_rpm,
            gear=self.physics.gear,
            wheel_speeds=tuple(self.physics.wheel_speeds),
            tire_slip_ratios=(0.0, 0.0, 0.0, 0.0),  # Simplified
            suspension_travel=(0.0, 0.0, 0.0, 0.0),  # Simplified
            track_x=self.physics.position[0],
            track_y=self.physics.position[1],
            heading=self.physics.heading,
            distance_to_centerline=self.physics.position[1],
            track_progress=self.track_progress,
            current_curvature=track_data['curvature'],
            upcoming_curvature=track_data['upcoming_curvature'],
            track_gradient=track_data['gradient'],
            distance_to_apex=50.0,  # Simplified
            apex_radius=1.0 / abs(track_data['curvature']) if track_data['curvature'] != 0 else 1000.0,
            dist_left_edge=dist_left,
            dist_right_edge=dist_right,
            front_ray=100.0,  # Simplified
            front_left_ray=80.0,
            front_right_ray=80.0,
            # Degradation state (new)
            tire_wear=self.physics.tire_state.wear,
            tire_grip_mult=self.physics.tire_state.grip_multiplier,
            fuel_remaining=self.physics.fuel_state.current_kg,
            fuel_normalized=self.physics.fuel_state.normalized,
            weather_grip=self.weather.grip_mu if self.weather else 1.2,
            rain_intensity=self.weather.rain_intensity if self.weather else 0.0,
            # Metadata
            current_section=track_data['section'],
            timestamp=self.tick * self.physics.DT,
            tick=self.tick
        )
    
    def step(self, control: ControlInput) -> VehicleState:
        """
        Execute one simulation step.
        
        Args:
            control: Control inputs from AI or expert
        
        Returns:
            Updated vehicle state
        """
        # Get track data
        track_data = self.track.get_track_data(self.track_progress)
        
        # Update weather (if enabled)
        if self.weather:
            self.weather.tick(self.rng)
        
        # Advance physics (now includes tire/fuel/weather)
        long_accel, lat_accel, steering_angle = self.physics.step(
            control,
            track_data['curvature'],
            track_data['gradient'],
            self.weather
        )
        
        # Update track progress
        distance_traveled = self.physics.velocity * self.physics.DT
        self.track_progress += distance_traveled / self.track.TRACK_LENGTH
        
        # Check lap completion
        if self.track_progress >= 1.0:
            self.current_lap += 1
            self.track_progress = 0.0
            print(f"✓ Lap {self.current_lap} complete!")
        
        # Build state
        state = self.get_current_state(track_data)
        state.longitudinal_accel = long_accel
        state.lateral_accel = lat_accel
        state.steering_angle = steering_angle
        state.throttle_input = control.throttle_command
        state.brake_input = control.brake_command
        
        # Record state-action pair
        self.state_action_history.append({
            'state': asdict(state),
            'action': asdict(control),
            'tick': self.tick
        })
        
        self.tick += 1
        return state
    
    def step_with_pit(
        self,
        control: ControlInput,
        pit_signal: float=0.0,
        pit_compound: TireCompound=TireCompound.MEDIUM,
        pit_fuel: float=110.0
    ) -> Tuple[VehicleState, float]:
        """
        Execute one simulation step with pit signal support.
        
        Args:
            control: Control inputs from AI or expert
            pit_signal: 0.0-1.0, triggers pit if above threshold
            pit_compound: Tire compound to use on pit stop
            pit_fuel: Fuel amount on pit stop
        
        Returns:
            (state, reward_modifier) - reward_modifier is -10 during pit
        """
        reward_modifier = 0.0
        
        # Process pit time if in pit
        if self._process_pit_time():
            # Still in pit - no physics update
            reward_modifier = -10.0  # Pit penalty for RL
            track_data = self.track.get_track_data(self.track_progress)
            state = self.get_current_state(track_data)
            self.tick += 1
            return state, reward_modifier
        
        # Check for pit entry trigger
        tire_wear = self.physics.tire_state.wear
        fuel = self.physics.fuel_state.current_kg
        
        # Dynamic threshold: lower if urgent
        pit_threshold = 0.7 if (tire_wear > 0.6 or fuel < 20) else 0.8
        
        if pit_signal > pit_threshold and not self.in_pit:
            self.trigger_pit_entry(pit_compound, pit_fuel)
            reward_modifier = -10.0
            track_data = self.track.get_track_data(self.track_progress)
            state = self.get_current_state(track_data)
            self.tick += 1
            return state, reward_modifier
        
        # Normal physics step
        state = self.step(control)
        return state, reward_modifier
    
    def get_rl_observation(self) -> np.ndarray:
        """Get normalized observation vector for RL training."""
        tire_wear = self.physics.tire_state.wear
        fuel_kg = self.physics.fuel_state.current_kg
        
        return np.array([
            self.physics.velocity / 80.0,  # Normalized speed
            tire_wear,  # 0-1
            fuel_kg / 110.0,  # 0-1
            (self.weather.grip_mu if self.weather else 1.2) / 1.2,  # Normalized grip
            self.current_lap / 50.0,  # Progress (assuming 50 lap race)
            1.0 if self.in_pit else 0.0,  # Pit status
            self.pit_urgency(tire_wear, fuel_kg),  # Learned signal
            self.pit_remaining_time / self.pit_time_penalty if self.in_pit else 0.0  # Pit progress
        ], dtype=np.float32)
    
    def create_checkpoint(self) -> Dict[str, Any]:
        """
        Create checkpoint with SSOT lineage tracking.
        Compatible with enterprise_business_game checkpoint format.
        """
        # Compute state vector hash (now includes degradation state)
        state_payload = {
            'position': self.physics.position.tolist(),
            'velocity': float(self.physics.velocity),
            'heading': float(self.physics.heading),
            'gear': self.physics.gear,
            'track_progress': float(self.track_progress),
            'lap': self.current_lap,
            # Degradation state (new)
            'tire_wear': float(self.physics.tire_state.wear),
            'tire_compound': self.physics.tire_state.compound.value,
            'fuel_kg': float(self.physics.fuel_state.current_kg),
            'weather_grip': float(self.weather.grip_mu) if self.weather else 1.2,
            'rain_intensity': float(self.weather.rain_intensity) if self.weather else 0.0
        }
        
        state_json = json.dumps(state_payload, sort_keys=True, separators=(',', ':'))
        state_hash = hashlib.sha256(state_json.encode('utf-8')).hexdigest()
        
        # Build checkpoint
        checkpoint = {
            'checkpoint_id': f'racing_ckpt_{self.tick}',
            'tick': self.tick,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'game_seed': self.seed,
            'state_vector': state_payload,
            'canonical_sha256': state_hash,
            'lap': self.current_lap,
            'track_progress': self.track_progress,
            'simulation_time': self.tick * self.physics.DT,
            'state_history_count': len(self.state_action_history)
        }
        
        # IPFS integration (if available)
        if self.ipfs_bridge:
            try:
                ipfs_result = self.ipfs_bridge.pin_checkpoint(checkpoint)
                checkpoint['ipfs_cid'] = ipfs_result['cid']
                checkpoint['multihash'] = ipfs_result['multihash']
                checkpoint['storage_uri'] = ipfs_result['uri']
            except Exception as e:
                print(f"⚠️  IPFS pinning failed: {e}")
        
        return checkpoint
    
    def export_training_data(self, filename: str="nurburgring_training.ndjson"):
        """
        Export state-action history as NDJSON for Random Forest training.
        """
        with open(filename, 'w') as f:
            for record in self.state_action_history:
                f.write(json.dumps(record) + '\n')
        
        print(f"✓ Exported {len(self.state_action_history)} training samples to {filename}")
        return filename
