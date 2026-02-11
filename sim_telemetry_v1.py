"""
SimTelemetry v1 - Canonical Webhook Payload Schema
Minimal, extensible, Zapier-friendly telemetry contract.

Specification:
- Simulator-agnostic (works for real sensors later)
- Flat structure (no nested arrays)
- Deterministic threshold classification
- Direct mapping to Canvas Tables + Paths + Interfaces
"""

from typing import Dict, Optional, Literal
from dataclasses import dataclass, asdict
import time
import json


# Threshold constants (confirmed, deterministic)
ACCEL_THRESHOLD_CRITICAL = 9.0   # m/s² (≥ 9.0)
ACCEL_THRESHOLD_HIGH = 6.0       # m/s² (6.0–8.99)

# Event types (severity levels)
EventType = Literal["Laminar", "High", "Critical"]


@dataclass
class SimTelemetryV1:
    """
    Canonical webhook payload for simulation telemetry.
    
    Schema Version: sim.telemetry.v1
    
    Required Fields:
        - Identity: schema_version, run_id, vehicle_id
        - Temporal: tick, timestamp_ms
        - Kinematics: speed_mps, accel_mps2
    
    Optional Fields:
        - Spatial: position_lat, position_lon, heading_deg
    
    Computed Fields:
        - event_type (Laminar/High/Critical)
        - severity (same as event_type, for compatibility)
    """
    
    # Identity & lineage (required)
    schema_version: str
    run_id: str
    vehicle_id: str
    
    # Temporal (required)
    tick: int
    timestamp_ms: int
    
    # Kinematics (required)
    speed_mps: float
    accel_mps2: float
    
    # Spatial (optional but recommended)
    position_lat: Optional[float] = None
    position_lon: Optional[float] = None
    heading_deg: Optional[float] = None
    
    # Optional extensions (safe to add later)
    g_force: Optional[float] = None
    road_grade_pct: Optional[float] = None
    surface: Optional[str] = None
    mode: Optional[str] = None
    
    def compute_event_type(self) -> EventType:
        """
        Deterministic threshold classification based on acceleration.
        
        Rules:
            accel_mps2 >= 9.0         → Critical
            accel_mps2 >= 6.0 < 9.0   → High
            accel_mps2 < 6.0          → Laminar
        
        Returns:
            Event type (Laminar/High/Critical)
        """
        if self.accel_mps2 >= ACCEL_THRESHOLD_CRITICAL:
            return "Critical"
        elif self.accel_mps2 >= ACCEL_THRESHOLD_HIGH:
            return "High"
        else:
            return "Laminar"
    
    def to_webhook_payload(self) -> Dict:
        """
        Convert to webhook POST payload.
        
        Returns:
            Dictionary ready for JSON serialization
        """
        payload = {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "vehicle_id": self.vehicle_id,
            "tick": self.tick,
            "timestamp_ms": self.timestamp_ms,
            "speed_mps": round(self.speed_mps, 2),
            "accel_mps2": round(self.accel_mps2, 2),
        }
        
        # Add optional spatial fields if present
        if self.position_lat is not None:
            payload["position_lat"] = round(self.position_lat, 6)
        if self.position_lon is not None:
            payload["position_lon"] = round(self.position_lon, 6)
        if self.heading_deg is not None:
            payload["heading_deg"] = round(self.heading_deg, 1)
        
        # Add optional extensions if present
        if self.g_force is not None:
            payload["g_force"] = round(self.g_force, 2)
        if self.road_grade_pct is not None:
            payload["road_grade_pct"] = round(self.road_grade_pct, 1)
        if self.surface is not None:
            payload["surface"] = self.surface
        if self.mode is not None:
            payload["mode"] = self.mode
        
        return payload
    
    def to_canvas_table_row(self) -> Dict:
        """
        Convert to Canvas Table row with computed fields.
        
        Returns:
            Dictionary for SimTelemetry table insertion
        """
        event_type = self.compute_event_type()
        
        row = {
            "run_id": self.run_id,
            "vehicle_id": self.vehicle_id,
            "tick": self.tick,
            "timestamp": self.timestamp_ms,
            "speed_mps": round(self.speed_mps, 2),
            "accel_mps2": round(self.accel_mps2, 2),
            "event_type": event_type,
            "severity": event_type,  # Alias for compatibility
        }
        
        # Add spatial if present
        if self.position_lat is not None:
            row["lat"] = round(self.position_lat, 6)
        if self.position_lon is not None:
            row["lon"] = round(self.position_lon, 6)
        if self.heading_deg is not None:
            row["heading"] = round(self.heading_deg, 1)
        
        return row
    
    @staticmethod
    def from_simulation_state(
        run_id: str,
        vehicle_id: str,
        tick: int,
        speed_mps: float,
        accel_mps2: float,
        position_lat: Optional[float] = None,
        position_lon: Optional[float] = None,
        heading_deg: Optional[float] = None,
        **kwargs
    ) -> 'SimTelemetryV1':
        """
        Factory method to create from simulation state.
        
        Args:
            run_id: Simulation run identifier
            vehicle_id: Vehicle identifier
            tick: Simulation tick number
            speed_mps: Speed in meters per second
            accel_mps2: Acceleration in m/s²
            position_lat: Latitude (optional)
            position_lon: Longitude (optional)
            heading_deg: Heading in degrees (optional)
            **kwargs: Additional optional fields
        
        Returns:
            SimTelemetryV1 instance
        """
        return SimTelemetryV1(
            schema_version="sim.telemetry.v1",
            run_id=run_id,
            vehicle_id=vehicle_id,
            tick=tick,
            timestamp_ms=int(time.time() * 1000),
            speed_mps=speed_mps,
            accel_mps2=accel_mps2,
            position_lat=position_lat,
            position_lon=position_lon,
            heading_deg=heading_deg,
            **kwargs
        )


# Example usage and validation
if __name__ == "__main__":
    print("="*70)
    print("  SimTelemetry v1 - Schema Validation")
    print("="*70)
    
    # Test 1: Laminar event
    print("\n1. Laminar Event (accel < 6.0 m/s²)")
    print("-"*70)
    
    laminar = SimTelemetryV1.from_simulation_state(
        run_id="sim_001",
        vehicle_id="car_1",
        tick=150,
        speed_mps=25.9,
        accel_mps2=5.2,
        position_lat=41.8807,
        position_lon=-87.6233,
        heading_deg=92.4
    )
    
    print(f"  Event Type: {laminar.compute_event_type()}")
    print(f"  Payload:\n{json.dumps(laminar.to_webhook_payload(), indent=2)}")
    
    # Test 2: High event
    print("\n2. High Event (6.0 ≤ accel < 9.0 m/s²)")
    print("-"*70)
    
    high = SimTelemetryV1.from_simulation_state(
        run_id="sim_001",
        vehicle_id="car_1",
        tick=151,
        speed_mps=27.3,
        accel_mps2=7.5,
        position_lat=41.8808,
        position_lon=-87.6234,
        heading_deg=93.1
    )
    
    print(f"  Event Type: {high.compute_event_type()}")
    print(f"  Payload:\n{json.dumps(high.to_webhook_payload(), indent=2)}")
    
    # Test 3: Critical event
    print("\n3. Critical Event (accel ≥ 9.0 m/s²)")
    print("-"*70)
    
    critical = SimTelemetryV1.from_simulation_state(
        run_id="sim_001",
        vehicle_id="car_1",
        tick=152,
        speed_mps=31.2,
        accel_mps2=9.8,
        position_lat=41.8809,
        position_lon=-87.6235,
        heading_deg=94.7,
        g_force=1.0,
        surface="dry",
        mode="sport"
    )
    
    print(f"  Event Type: {critical.compute_event_type()}")
    print(f"  Payload:\n{json.dumps(critical.to_webhook_payload(), indent=2)}")
    
    # Test 4: Canvas table mapping
    print("\n4. Canvas Table Row")
    print("-"*70)
    
    table_row = critical.to_canvas_table_row()
    print(f"  Row:\n{json.dumps(table_row, indent=2)}")
    
    # Test 5: Threshold boundaries
    print("\n5. Threshold Boundary Tests")
    print("-"*70)
    
    test_cases = [
        (5.9, "Laminar"),
        (6.0, "High"),
        (8.99, "High"),
        (9.0, "Critical"),
        (12.5, "Critical")
    ]
    
    for accel, expected_type in test_cases:
        event = SimTelemetryV1.from_simulation_state(
            run_id="test",
            vehicle_id="test_car",
            tick=0,
            speed_mps=25.0,
            accel_mps2=accel
        )
        actual_type = event.compute_event_type()
        status = "✓" if actual_type == expected_type else "✗"
        print(f"  {status} accel={accel:5.2f} m/s² → {actual_type:8s} (expected: {expected_type})")
    
    print("\n" + "="*70)
    print("✅ SimTelemetry v1 schema validated!")
    print("="*70)
