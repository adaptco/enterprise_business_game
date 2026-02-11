# SimTelemetry v1 — Canonical Webhook Payload Schema

## Authoritative POST Contract

**Schema:** `sim.telemetry.v1`  
**Status:** ✅ Production-ready (threshold validation complete)  
**Last Updated:** 2026-01-12

---

## Minimal Payload Example

```json
{
  "schema_version": "sim.telemetry.v1",
  "run_id": "sim_001",
  "vehicle_id": "car_1",
  "tick": 150,
  "timestamp_ms": 1715123456789,
  "speed_mps": 25.9,
  "accel_mps2": 7.2,
  "position_lat": 41.8807,
  "position_lon": -87.6233,
  "heading_deg": 92.4
}
```

---

## Field Specification

### Identity & Lineage (Required)

| Field | Type | Purpose | Example |
|-------|------|---------|---------|
| `schema_version` | string | Forward compatibility + audit | `"sim.telemetry.v1"` |
| `run_id` | string | Groups all ticks from a simulation | `"sim_001"` |
| `vehicle_id` | string | Supports multi-vehicle runs | `"car_1"` |

**Usage:** Enables replay, slicing, and audit trail.

---

### Temporal Fields (Required)

| Field | Type | Purpose | Example |
|-------|------|---------|---------|
| `tick` | integer | Deterministic simulation step | `150` |
| `timestamp_ms` | integer | Wall-clock ordering & joins | `1715123456789` |

**Zapier Note:** Integers preferred over ISO timestamps (no parsing required).

---

### Kinematics (Required)

| Field | Type | Purpose | Example |
|-------|------|---------|---------|
| `speed_mps` | number | Informational + future logic | `25.9` |
| `accel_mps2` | number | **Primary classification signal** | `7.2` |

**Classification Rules:**
```
accel_mps2 < 6.0         → Laminar
accel_mps2 >= 6.0 < 9.0  → High
accel_mps2 >= 9.0        → Critical
```

**Validation Results:**
```
✅ 5.90 m/s² → Laminar
✅ 6.00 m/s² → High
✅ 8.99 m/s² → High
✅ 9.00 m/s² → Critical
✅ 12.5 m/s² → Critical
```

---

### Spatial Context (Optional but Recommended)

| Field | Type | Purpose | Example |
|-------|------|---------|---------|
| `position_lat` | number | Mapping, clustering | `41.8807` |
| `position_lon` | number | Mapping, clustering | `-87.6233` |
| `heading_deg` | number | Orientation, future braking logic | `92.4` |

**Canvas Note:** Enables geospatial dashboards and heatmaps.

---

## Explicitly Not Included (By Design)

These are **intentionally excluded** from v1 to keep Zapier logic simple:

| Field | Reason |
|-------|--------|
| ❌ G-force | Derivable: `accel_mps2 / 9.81` |
| ❌ accel_x / accel_y | Only add if you need braking vs throttle separation |
| ❌ fuel / battery SOC | Belongs to Powertrain schema |
| ❌ engine RPM | Belongs to Drivetrain schema |
| ❌ Nested objects/arrays | Zapier pain |

**Extension Path:** Add as v1.1 without breaking Canvas.

---

## Optional Extensions (Safe to Add)

```json
{
  "g_force": 0.73,
  "road_grade_pct": -2.1,
  "surface": "dry",
  "mode": "sport"
}
```

Canvas Copilot ignores unused fields.

---

## Canvas Table Mapping

**Table:** `SimTelemetry`

| Table Field | Webhook Field | Computed |
|-------------|---------------|----------|
| run_id | run_id | |
| vehicle_id | vehicle_id | |
| tick | tick | |
| timestamp | timestamp_ms | |
| speed_mps | speed_mps | |
| accel_mps2 | accel_mps2 | |
| lat | position_lat | |
| lon | position_lon | |
| heading | heading_deg | |
| event_type | *(computed)* | ✅ |
| severity | *(computed)* | ✅ |

**Computed Fields Logic:**
```python
if accel_mps2 >= 9.0:
    event_type = "Critical"
elif accel_mps2 >= 6.0:
    event_type = "High"
else:
    event_type = "Laminar"

severity = event_type  # Alias for compatibility
```

---

## Zapier Paths Logic (Deterministic)

### Critical Path
```
Trigger: Webhook POST
Filter: accel_mps2 >= 9.0
Action: Insert to SimTelemetry table with event_type="Critical"
```

### High Path
```
Trigger: Webhook POST
Filter: accel_mps2 >= 6.0 AND accel_mps2 < 9.0
Action: Insert to SimTelemetry table with event_type="High"
```

### Laminar Path (Default)
```
Trigger: Webhook POST
Filter: (default path)
Action: Insert to SimTelemetry table with event_type="Laminar"
```

**No ambiguity. No overlap.**

---

## Why This Schema is the Right Handoff Point

✅ **Zapier-Friendly**
- One POST = one row
- One numeric field drives classification
- No hidden derivations

✅ **Simulator-Agnostic**  
- Works identically for:
  - Python simulators
  - TypeScript simulators
  - Replay systems
  - Real vehicles later

✅ **Canvas-Ready**
- Webhook → Table (direct mapping)
- Table → Paths (threshold classification)
- Paths → Interface (summary views)
- Interface → Dashboards (no drift)

✅ **Extensible Without Breaking**
- v1.1 can add optional fields
- Existing Canvas flows ignore unknown fields
- No schema migration required

---

## Implementation Status

**Python Reference Implementation:**
- ✅ `sim_telemetry_v1.py` (dataclass + validation)
- ✅ Threshold classification (5 boundary tests passed)
- ✅ Webhook payload generation
- ✅ Canvas table row mapping

**Next Steps:**
1. GT Racing adapter (emit SimTelemetry v1 payloads)
2. Canvas orchestration contract
3. Zapier webhook receiver setup
4. Interface wiring (Canvas Copilot)

---

## Example Payloads

### Laminar (Cruising)
```json
{
  "schema_version": "sim.telemetry.v1",
  "run_id": "sim_001",
  "vehicle_id": "car_1",
  "tick": 150,
  "timestamp_ms": 1768236432836,
  "speed_mps": 25.9,
  "accel_mps2": 5.2,
  "position_lat": 41.8807,
  "position_lon": -87.6233,
  "heading_deg": 92.4
}
```
**Event Type:** `Laminar`

### High (Accelerating)
```json
{
  "schema_version": "sim.telemetry.v1",
  "run_id": "sim_001",
  "vehicle_id": "car_1",
  "tick": 151,
  "timestamp_ms": 1768236432836,
  "speed_mps": 27.3,
  "accel_mps2": 7.5,
  "position_lat": 41.8808,
  "position_lon": -87.6234,
  "heading_deg": 93.1
}
```
**Event Type:** `High`

### Critical (Hard Acceleration)
```json
{
  "schema_version": "sim.telemetry.v1",
  "run_id": "sim_001",
  "vehicle_id": "car_1",
  "tick": 152,
  "timestamp_ms": 1768236432840,
  "speed_mps": 31.2,
  "accel_mps2": 9.8,
  "position_lat": 41.8809,
  "position_lon": -87.6235,
  "heading_deg": 94.7,
  "g_force": 1.0,
  "surface": "dry",
  "mode": "sport"
}
```
**Event Type:** `Critical`

---

## ✅ **Final Confirmation**

The `SimTelemetry.v1` schema is now the **authoritative contract** for:
- All simulators (Python, TypeScript, etc.)
- Webhook emissions
- Canvas table ingestion  
- Zapier path routing

**Status:** Ready for Canvas orchestration wire-up.
