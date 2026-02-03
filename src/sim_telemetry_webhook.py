"""
SimTelemetry Webhook Emitter
Emits canonical SimTelemetry.v1 payloads for Zapier/Canvas integration.

Threshold Classification:
- Laminar:  accel < 6.0 m/s²
- High:     6.0 ≤ accel < 9.0 m/s²
- Critical: accel ≥ 9.0 m/s²
"""

import json
import time
import requests
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime, timezone


@dataclass
class SimTelemetryPayload:
    """
    Canonical webhook payload for simulation telemetry.
    Maps directly to SimTelemetry.v1 schema.
    """
    # Required fields
    schema_version: str = "sim.telemetry.v1"
    run_id: str = ""
    vehicle_id: str = ""
    tick: int = 0
    timestamp_ms: int = 0
    speed_mps: float = 0.0
    accel_mps2: float = 0.0
    
    # Optional spatial fields
    position_lat: Optional[float] = None
    position_lon: Optional[float] = None
    heading_deg: Optional[float] = None
    
    # Optional extension fields
    g_force: Optional[float] = None
    road_grade_pct: Optional[float] = None
    surface: Optional[str] = None
    mode: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values"""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    def to_json(self) -> str:
        """Convert to canonical JSON string"""
        return json.dumps(self.to_dict(), separators=(',', ':'))
    
    @property
    def severity(self) -> str:
        """
        Compute severity based on acceleration thresholds.
        
        Returns:
            "Critical", "High", or "Laminar"
        """
        if self.accel_mps2 >= 9.0:
            return "Critical"
        elif self.accel_mps2 >= 6.0:
            return "High"
        else:
            return "Laminar"
    
    @property
    def event_type(self) -> str:
        """
        Determine event type based on acceleration.
        
        Returns:
            "hard_accel", "moderate_accel", or "normal"
        """
        if self.accel_mps2 >= 9.0:
            return "hard_accel"
        elif self.accel_mps2 >= 6.0:
            return "moderate_accel"
        else:
            return "normal"


class WebhookEmitter:
    """
    Emits SimTelemetry payloads to webhook endpoints.
    Designed for Zapier/Canvas integration.
    """
    
    def __init__(
        self,
        webhook_url: Optional[str] = None,
        local_storage: bool = True,
        storage_file: str = "telemetry_log.ndjson"
    ):
        """
        Initialize webhook emitter.
        
        Args:
            webhook_url: Zapier/Canvas webhook URL (None = dry run)
            local_storage: Save payloads locally as NDJSON
            storage_file: Local storage file path
        """
        self.webhook_url = webhook_url
        self.local_storage = local_storage
        self.storage_file = storage_file
        self.payloads_sent = 0
        self.errors = []
    
    def emit(self, payload: SimTelemetryPayload) -> bool:
        """
        Emit payload to webhook and/or local storage.
        
        Args:
            payload: SimTelemetry payload to emit
        
        Returns:
            True if successful, False otherwise
        """
        success = True
        
        # Store locally
        if self.local_storage:
            try:
                with open(self.storage_file, 'a') as f:
                    f.write(payload.to_json() + '\n')
            except Exception as e:
                self.errors.append(f"Local storage error: {e}")
                success = False
        
        # Send to webhook
        if self.webhook_url:
            try:
                response = requests.post(
                    self.webhook_url,
                    json=payload.to_dict(),
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                response.raise_for_status()
                self.payloads_sent += 1
            except requests.exceptions.RequestException as e:
                self.errors.append(f"Webhook error: {e}")
                success = False
        
        return success
    
    def emit_batch(self, payloads: List[SimTelemetryPayload]) -> int:
        """
        Emit multiple payloads.
        
        Returns:
            Number of successful emissions
        """
        success_count = 0
        for payload in payloads:
            if self.emit(payload):
                success_count += 1
        return success_count


def create_telemetry_from_vehicle(
    vehicle_state: Dict[str, Any],
    run_id: str,
    tick: int,
    accel_mps2: float
) -> SimTelemetryPayload:
    """
    Create telemetry payload from GT Racing vehicle state.
    
    Args:
        vehicle_state: Vehicle state dict with x, y, heading, velocity
        run_id: Simulation run identifier
        tick: Current tick number
        accel_mps2: Computed acceleration
    
    Returns:
        SimTelemetryPayload ready for emission
    """
    # Convert position to lat/lon (simplified — real implementation would use projection)
    # For demo, treat x/y as meters from origin and convert to degrees
    METERS_PER_DEGREE = 111320.0  # At equator
    position_lat = 41.8807 + (vehicle_state.get('y', 0) / METERS_PER_DEGREE)
    position_lon = -87.6233 + (vehicle_state.get('x', 0) / (METERS_PER_DEGREE * 0.7))  # Adjust for latitude
    
    # Convert heading from radians to degrees
    import math
    heading_deg = math.degrees(vehicle_state.get('heading', 0)) % 360
    
    # Compute g-force
    g_force = accel_mps2 / 9.81
    
    return SimTelemetryPayload(
        run_id=run_id,
        vehicle_id=vehicle_state.get('id', 'car_1'),
        tick=tick,
        timestamp_ms=int(time.time() * 1000),
        speed_mps=vehicle_state.get('velocity', 0),
        accel_mps2=accel_mps2,
        position_lat=position_lat,
        position_lon=position_lon,
        heading_deg=heading_deg,
        g_force=g_force
    )


def demo_webhook_emitter():
    """Demonstrate webhook emitter with sample data"""
    print("\n" + "="*60)
    print("📡 SIMTELEMETRY WEBHOOK EMITTER DEMO")
    print("="*60)
    
    # Create emitter (local storage only, no webhook)
    emitter = WebhookEmitter(
        webhook_url=None,  # Set to Zapier URL when ready
        local_storage=True,
        storage_file="demo_telemetry.ndjson"
    )
    
    print("\n📊 Generating sample telemetry...")
    
    # Simulate acceleration from 0 to 12 m/s² over 10 ticks
    payloads = []
    for tick in range(10):
        accel = tick * 1.2  # Ramps from 0 to 10.8 m/s²
        
        payload = SimTelemetryPayload(
            run_id="sim_demo_001",
            vehicle_id="car_1",
            tick=tick,
            timestamp_ms=int(time.time() * 1000) + (tick * 100),
            speed_mps=5.0 + (tick * 2.0),
            accel_mps2=accel,
            position_lat=41.8807,
            position_lon=-87.6233,
            heading_deg=90.0
        )
        
        payloads.append(payload)
        
        # Show classification
        severity = payload.severity
        print(f"  Tick {tick}: {accel:4.1f} m/s² → {severity:8s}")
    
    # Emit all payloads
    print(f"\n📤 Emitting {len(payloads)} payloads...")
    success_count = emitter.emit_batch(payloads)
    
    print(f"\n✅ Emitted {success_count}/{len(payloads)} successfully")
    print(f"📁 Saved to: {emitter.storage_file}")
    
    # Show threshold distribution
    print(f"\n📈 Severity Distribution:")
    laminar = sum(1 for p in payloads if p.severity == "Laminar")
    high = sum(1 for p in payloads if p.severity == "High")
    critical = sum(1 for p in payloads if p.severity == "Critical")
    
    print(f"  Laminar:  {laminar} ({laminar/len(payloads)*100:.0f}%)")
    print(f"  High:     {high} ({high/len(payloads)*100:.0f}%)")
    print(f"  Critical: {critical} ({critical/len(payloads)*100:.0f}%)")
    
    print("\n" + "="*60)
    print("✅ SimTelemetry webhook emitter ready for Zapier integration")
    print("="*60)


if __name__ == "__main__":
    demo_webhook_emitter()
