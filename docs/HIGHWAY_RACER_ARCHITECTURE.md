# Highway Racer: Unity Architecture Pack

## Cel-Shaded Open-World Highway Racer with Tokyo Extreme Racer–Style Battles

> Implementation-ready architecture for mobile (iOS/Android), Unity URP, 30-60 FPS

---

## 1. EXEC SUMMARY

1. **Target Platform**: iOS/Android midrange devices (A12+, Snapdragon 730+), 30-60 FPS
2. **Engine**: Unity 2022.3 LTS with URP; C# patterns optimized for mobile GC
3. **Visual Style**: Cel-shaded toon shading with inverted-hull outlines; minimal post-processing
4. **World Structure**: Open-world highway network using streaming cells (256m × 256m)
5. **Core Loop**: Free-roam highways → spot rival → headlight flash challenge → SP battle → win/lose → progression
6. **Battle Mechanic**: Tokyo Extreme Racer–style SP drain; leader drains follower's SP bar
7. **Physics**: Arcade-real hybrid with drift assist and collision response at 50Hz fixed timestep
8. **Streaming**: Predictive loading along highway graph; max 2 cell loads/sec, 150MB memory ceiling
9. **Progression**: Rep/cash economy, rival roster unlocks, car upgrades, team leader boss battles
10. **Governance**: Fail-closed save system with battle replay seeds for deterministic verification

---

## 2. GAME LOOP & MODE STATE MACHINE

```text
                    ┌────────────────────────────────────────┐
                    │              BOOT                      │
                    │  (Load core bundles, validate save)    │
                    └────────────────┬───────────────────────┘
                                     │ save_valid
                                     ▼
                    ┌────────────────────────────────────────┐
                    │            MAIN_MENU                   │
                    │  (Garage, Settings, Continue/New)      │
                    └────────────────┬───────────────────────┘
                                     │ select_continue OR select_new
                                     ▼
┌───────────────────────────────────────────────────────────────────────┐
│                           FREE_ROAM                                    │
│  Player drives open-world highways. Rivals spawn. Traffic flows.       │
│                                                                        │
│  Events:                                                               │
│    - rival_spotted → show target indicator                             │
│    - player_flash_headlights + in_lock_envelope → transition BATTLE    │
│    - rival_flash_headlights + player_accepts → transition BATTLE       │
│    - player_pause → transition PAUSE_MENU                              │
│    - enter_garage_zone → transition GARAGE                             │
└────────────────────────────────┬──────────────────────────────────────┘
                                 │ initiate_battle
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│                              BATTLE                                    │
│  SP bars active. Gap-based drain. No pause. Traffic thins.            │
│                                                                        │
│  Sub-states:                                                           │
│    COUNTDOWN (3s) → ACTIVE → FINISHED                                  │
│                                                                        │
│  Transitions:                                                          │
│    - player_sp <= 0 → DEFEAT                                           │
│    - rival_sp <= 0 → VICTORY                                           │
│    - either_crashes → FORFEIT (crasher loses)                          │
│    - distance > 500m for 10s → DISENGAGE (no winner)                   │
└────────────────────────────────┬──────────────────────────────────────┘
                                 │ battle_end
                                 ▼
┌───────────────────────────────────────────────────────────────────────┐
│                          BATTLE_RESULT                                 │
│  Show outcome, rep/cash earned, unlocks. 5s auto-dismiss or tap.       │
└────────────────────────────────┬──────────────────────────────────────┘
                                 │ dismiss
                                 ▼
                            FREE_ROAM (loop)

Guards:
  - in_lock_envelope: distance < 100m AND same_highway_segment AND speed > 20m/s AND LOS_clear
  - rival_accepts: 80% chance for wanderers, 100% for bosses
  - enter_garage_zone: collider trigger at designated locations
```

---

## 3. SYSTEMS OVERVIEW (MODULE MAP)

| Module | Responsibility | Dependencies |
|--------|----------------|--------------|
| **GameModeController** | State machine for BOOT→MENU→FREEROAM→BATTLE→RESULT | None (root) |
| **WorldStreamingManager** | Load/unload cells, manage pools, predictive loading | HighwayGraph |
| **HighwayGraph** | Node-edge representation of highway network, lane queries | None |
| **VehicleController** | Physics, input handling, drift/boost mechanics | InputManager |
| **InputManager** | Abstract input (touch/tilt/gamepad) to InputIntent | None |
| **TrafficManager** | Spawn/despawn ambient traffic, avoid player lane | WorldStreamingManager |
| **RivalManager** | Spawn rivals, track visibility, manage AI drivers | WorldStreamingManager, AIBehavior |
| **AIBehavior** | Rival driving AI (racing line, pressure, recovery) | VehicleController |
| **BattleManager** | SP calculation, win/loss, battle events | RivalManager, SPBarModel |
| **HeadlightFlashSystem** | Challenge initiation, lock envelope validation | BattleManager |
| **SPBarModel** | SP drain computation, tunables | None (data) |
| **ProgressionManager** | Rep, cash, unlocks, rival roster progression | SaveManager |
| **GarageManager** | Car selection, upgrades, tuning | ProgressionManager |
| **UIManager** | HUD, menus, SP bars, minimap | All (read-only) |
| **SaveManager** | Atomic save/load, validation, corruption recovery | None |
| **TelemetryManager** | Debug logging, performance metrics | All (passive) |
| **AudioManager** | Engine sounds, music, battle SFX | GameModeController |
| **CelShaderController** | Material swapping, outline config, LOD | WorldStreamingManager |

### Dependency Graph (Simplified)

```text
GameModeController
    ├── WorldStreamingManager
    │       ├── HighwayGraph
    │       ├── TrafficManager
    │       └── RivalManager
    │               └── AIBehavior
    ├── VehicleController
    │       └── InputManager
    ├── BattleManager
    │       ├── HeadlightFlashSystem
    │       └── SPBarModel
    ├── ProgressionManager
    │       └── SaveManager
    ├── GarageManager
    └── UIManager
```

---

## 4. TICK / UPDATE MODEL

### Tick Groups

| Tick Group | Frequency | Unity Callback | Systems |
|------------|-----------|----------------|---------|
| **PhysicsTick** | 50 Hz | FixedUpdate | VehicleController, TrafficManager (movement), collision |
| **AICognitionTick** | 10 Hz | Custom timer in Update | AIBehavior decisions, rival targeting, path planning |
| **StreamingTick** | 5 Hz | Custom timer in Update | WorldStreamingManager predictive loads |
| **BattleTick** | 50 Hz | FixedUpdate (synced with physics) | BattleManager SP drain, distance checks |
| **UITick** | 30 Hz | Update (frame-locked) | UIManager refresh, SP bar lerp |
| **SaveTick** | 0.1 Hz (every 10s) + on-demand | Coroutine | SaveManager auto-checkpoint |

### Rationale

- **PhysicsTick at 50Hz**: Standard Unity physics, smooth on mobile, matches 60 FPS without jitter
- **AICognitionTick at 10Hz**: Expensive pathfinding/decisions; 100ms latency acceptable for racing AI
- **StreamingTick at 5Hz**: Prevents load spikes; predictive loading has ~200ms tolerance
- **BattleTick synced to Physics**: SP drain must match physics frame for determinism
- **UITick at 30Hz**: Sufficient for SP bar smoothness; halves UI overhead

### Code Pattern

```csharp
public class TickManager : MonoBehaviour
{
    private float _aiTimer;
    private float _streamTimer;
    private const float AI_INTERVAL = 0.1f;      // 10 Hz
    private const float STREAM_INTERVAL = 0.2f;  // 5 Hz

    void FixedUpdate()
    {
        PhysicsTick();  // 50 Hz
        BattleTick();   // Synced
    }

    void Update()
    {
        UITick();  // Every frame (target 30-60)

        _aiTimer += Time.deltaTime;
        if (_aiTimer >= AI_INTERVAL)
        {
            AICognitionTick();
            _aiTimer = 0f;
        }

        _streamTimer += Time.deltaTime;
        if (_streamTimer >= STREAM_INTERVAL)
        {
            StreamingTick();
            _streamTimer = 0f;
        }
    }
}
```

---

## 5. DATA MODEL (STRUCTS / SCHEMAS)

### PlayerProfile

```csharp
[Serializable]
public struct PlayerProfile
{
    public string PlayerId;           // GUID
    public string DisplayName;
    public int Rep;                   // Reputation points
    public int Cash;                  // In-game currency
    public int TotalBattlesWon;
    public int TotalBattlesLost;
    public string CurrentCarId;
    public List<string> OwnedCarIds;
    public List<string> DefeatedRivalIds;
    public int CurrentRank;           // 1-100
    public long LastSaveTimestamp;    // Unix ms
}
```

**JSON Schema:**

```json
{
  "playerId": "string (uuid)",
  "displayName": "string",
  "rep": "int",
  "cash": "int",
  "totalBattlesWon": "int",
  "totalBattlesLost": "int",
  "currentCarId": "string",
  "ownedCarIds": ["string"],
  "defeatedRivalIds": ["string"],
  "currentRank": "int",
  "lastSaveTimestamp": "long"
}
```

---

### CarSpec + HandlingTuning

```csharp
[Serializable]
public struct CarSpec
{
    public string CarId;
    public string DisplayName;
    public string Manufacturer;
    public CarClass Class;            // D, C, B, A, S
    public int BasePrice;
    public float BasePower;           // kW
    public float BaseWeight;          // kg
    public float BaseGrip;            // 0.0-2.0
    public float TopSpeed;            // m/s
    public string PrefabPath;         // Addressable key
}

[Serializable]
public struct HandlingTuning
{
    // All values 0.0-1.0, default 0.5
    public float SteeringSensitivity;
    public float ThrottleResponse;
    public float BrakeBalance;        // Front bias
    public float DriftAssist;         // Higher = easier drift
    public float StabilityControl;
    public float BoostPower;          // Multiplier
}

public enum CarClass { D, C, B, A, S }
```

---

### WorldCell + CellManifest

```csharp
[Serializable]
public struct WorldCell
{
    public string CellId;             // "cell_12_34"
    public Vector2Int GridPosition;   // (12, 34)
    public Bounds WorldBounds;        // 256m x 256m
    public string[] HighwaySegmentIds;
    public string[] PropGroupIds;     // Addressable keys
    public CellLODLevel CurrentLOD;
    public bool IsLoaded;
    public bool IsVisible;
}

[Serializable]
public struct CellManifest
{
    public string WorldId;
    public Vector2Int GridSize;       // e.g., (64, 64)
    public float CellSizeMeters;      // 256.0
    public List<CellEntry> Cells;
}

[Serializable]
public struct CellEntry
{
    public string CellId;
    public Vector2Int GridPos;
    public string AddressableKey;
    public int MemoryBudgetKB;
    public string[] AdjacentCellIds;
}

public enum CellLODLevel { Full, Reduced, Silhouette, Unloaded }
```

---

### HighwayGraph (Nodes, Lanes, Ramps)

```csharp
[Serializable]
public struct HighwayNode
{
    public string NodeId;
    public Vector3 WorldPosition;
    public NodeType Type;             // Straight, Curve, Junction, Ramp
    public string[] ConnectedNodeIds;
    public float SpeedLimit;          // m/s
}

[Serializable]
public struct HighwayLane
{
    public string LaneId;
    public string SegmentId;
    public int LaneIndex;             // 0 = leftmost
    public Vector3[] SplinePoints;    // Catmull-Rom control points
    public float Width;               // meters
}

[Serializable]
public struct HighwaySegment
{
    public string SegmentId;
    public string StartNodeId;
    public string EndNodeId;
    public List<HighwayLane> Lanes;
    public float Length;              // meters
    public SegmentType Type;          // Highway, Ramp, Tunnel, Bridge
}

public enum NodeType { Straight, Curve, Junction, RampEntry, RampExit }
public enum SegmentType { Highway, Ramp, Tunnel, Bridge, ServiceArea }
```

---

### TrafficSeed + SpawnBudget

```csharp
[Serializable]
public struct TrafficSeed
{
    public int GlobalSeed;            // Deterministic spawning
    public float Density;             // 0.0-1.0, affects spawn rate
    public float TruckRatio;          // % of traffic that are trucks
    public float AggressiveRatio;     // % that change lanes frequently
}

[Serializable]
public struct SpawnBudget
{
    public int MaxActiveVehicles;     // Default: 30
    public int MaxSpawnsPerSecond;    // Default: 2
    public float MinSpawnDistance;    // 150m ahead of player
    public float MaxSpawnDistance;    // 400m ahead of player
    public float DespawnDistance;     // 200m behind player
}
```

---

### RivalDefinition + RivalRoster

```csharp
[Serializable]
public struct RivalDefinition
{
    public string RivalId;
    public string DisplayName;
    public string TeamName;           // Nullable
    public RivalTier Tier;
    public string CarId;
    public CarClass MinPlayerClass;   // Player must have this to encounter
    public float BaseSPPool;          // Default: 1.0
    public float Aggression;          // 0.0-1.0
    public float SkillLevel;          // 0.0-1.0
    public int RepReward;
    public int CashReward;
    public string[] SpawnZoneIds;
    public string UnlockRequirement;  // JSON expression
    public Color CarColor;
    public Color HeadlightColor;
}

[Serializable]
public struct RivalRoster
{
    public List<RivalDefinition> Wanderers;
    public List<RivalDefinition> Bosses;
    public List<RivalDefinition> TeamLeaders;
    public Dictionary<string, int> PlayerVictories;  // rivalId -> win count
}

public enum RivalTier { Wanderer, Boss, TeamLeader }
```

---

### EncounterPreLock + BattleSession + SPBarModel

```csharp
[Serializable]
public struct EncounterPreLock
{
    public string RivalId;
    public float Distance;            // meters
    public bool InLockEnvelope;
    public bool LOSClear;
    public bool SameLane;
    public float RelativeSpeed;       // m/s
    public bool PlayerCanChallenge;
}

[Serializable]
public struct BattleSession
{
    public string BattleId;           // GUID
    public string RivalId;
    public long StartTimestamp;
    public int StartTick;
    public BattlePhase Phase;
    public float PlayerSP;
    public float RivalSP;
    public float GapMeters;
    public bool PlayerIsLeader;
    public int BattleSeed;            // For replay determinism
}

[Serializable]
public struct SPBarModel
{
    // Tunable drain rates
    public float BaseDrainPerSecond;      // Default: 0.03
    public float GapMultiplier;           // Default: 0.002 per meter
    public float SpeedMultiplier;         // Default: 0.008 per m/s
    public float EscalationRate;          // Default: 0.0002 per second
    public float MinDrainPerTick;         // Default: 0.0001
    public float MaxDrainPerTick;         // Default: 0.01
    public float CriticalThreshold;       // Default: 0.25
    public float CollisionDrainPenalty;   // Default: 0.05 instant
}

public enum BattlePhase { Pending, Countdown, Active, Finished }
```

---

### ProgressionUnlockGraph

```csharp
[Serializable]
public struct UnlockNode
{
    public string UnlockId;
    public UnlockType Type;           // Car, Rival, Zone, Upgrade
    public string TargetId;           // What gets unlocked
    public UnlockCondition Condition;
}

[Serializable]
public struct UnlockCondition
{
    public ConditionType Type;
    public string TargetId;           // e.g., rival_id, zone_id
    public int RequiredCount;         // e.g., 3 victories
    public int RequiredRep;           // Alternative: rep threshold
}

public enum UnlockType { Car, Rival, Zone, Upgrade, TeamLeader }
public enum ConditionType { DefeatRival, DefeatRivalCount, ZoneVictories, RepThreshold, OwnCar }
```

---

### TelemetryEvent

```csharp
[Serializable]
public struct TelemetryEvent
{
    public long Timestamp;            // Unix ms
    public int Tick;
    public TelemetryType Type;
    public string EventId;
    public Dictionary<string, object> Payload;
}

public enum TelemetryType
{
    BattleStart, BattleEnd, SPCritical,
    CellLoad, CellUnload, MemoryWarning,
    FrameDrop, InputLag, AIDecision,
    Crash, RivalSpawn, Unlock
}
```

---

## 6. WORLD STREAMING ARCHITECTURE

### Cell Sizing Strategy

- **Cell Size**: 256m × 256m (optimal for highway segments + memory budget)
- **Active Radius**: 3 cells ahead, 1 cell behind along highway path
- **Predicted Load**: 2 cells in travel direction based on velocity
- **Total Active**: Max 8 cells at any time

### Predictive Loading

```csharp
public class StreamingPredictor
{
    public List<string> GetCellsToLoad(
        Vector3 playerPos,
        Vector3 playerVelocity,
        HighwayGraph graph)
    {
        // 1. Find current highway segment
        var segment = graph.GetNearestSegment(playerPos);
        
        // 2. Project position 3 seconds ahead
        var predictedPos = playerPos + playerVelocity * 3f;
        
        // 3. Trace highway path to predicted position
        var pathCells = graph.TraceCellsAlongPath(
            segment, 
            predictedPos, 
            maxCells: 5
        );
        
        // 4. Add lateral cells (for lane changes)
        var lateralCells = GetAdjacentCells(pathCells);
        
        return pathCells.Concat(lateralCells).Distinct().ToList();
    }
}
```

### Pooling Policy

- **Prop Pool**: 200 generic props (barriers, signs, trees)
- **Vehicle Pool**: 40 traffic vehicles + 5 rival vehicles
- **Particle Pool**: 50 dust/spark emitters

### LOD + Collision Policy

| LOD Level | Distance | Mesh | Collision | Shadows |
|-----------|----------|------|-----------|---------|
| Full | 0-100m | High-poly | Mesh Collider | On |
| Reduced | 100-300m | Low-poly | Box Collider | Off |
| Silhouette | 300-500m | Billboard | None | Off |
| Unloaded | >500m | None | None | Off |

### Hard Budgets

- **Max Cell Loads/Sec**: 2
- **Max Instantiates/Frame**: 10 objects
- **Memory Ceiling**: 150 MB for streaming content
- **Load Queue Depth**: 4 cells maximum
- **Emergency Unload Trigger**: >140 MB

---

## 7. VEHICLE PHYSICS & INPUT ARCHITECTURE

### Arcade-Real Hybrid Design

```csharp
public class VehicleController : MonoBehaviour
{
    [Header("Core Physics")]
    public float EnginePower = 400f;          // kW
    public float BrakePower = 800f;           // kW
    public float Mass = 1400f;                // kg
    public float DragCoefficient = 0.3f;
    public float RollingResistance = 0.015f;

    [Header("Handling")]
    public float MaxSteerAngle = 35f;         // degrees
    public float SteerSpeed = 4f;             // degrees/sec
    public float GripMultiplier = 1.2f;
    public float DriftThreshold = 0.7f;       // slip ratio to enter drift
    public float DriftGripReduction = 0.5f;

    [Header("Assists")]
    [Range(0, 1)] public float TractionControl = 0.3f;
    [Range(0, 1)] public float StabilityAssist = 0.5f;
    [Range(0, 1)] public float DriftAssist = 0.4f;
    
    [Header("Boost")]
    public float BoostMultiplier = 1.5f;
    public float BoostDuration = 3f;          // seconds
    public float BoostCooldown = 10f;         // seconds
}
```

### Simplified Physics Model (50Hz)

```csharp
void FixedUpdate()
{
    // 1. Compute forces
    float throttleForce = _input.Throttle * EnginePower * 1000f / Mass;
    float brakeForce = _input.Brake * BrakePower * 1000f / Mass;
    float dragForce = 0.5f * DragCoefficient * _velocity.sqrMagnitude;
    
    // 2. Apply longitudinal acceleration
    float accel = throttleForce - brakeForce - dragForce - RollingResistance;
    _velocity += transform.forward * accel * Time.fixedDeltaTime;
    
    // 3. Apply steering (simplified Ackermann)
    float steerAngle = _input.Steer * MaxSteerAngle;
    float turnRadius = WheelBase / Mathf.Tan(steerAngle * Mathf.Deg2Rad);
    float angularVel = _velocity.magnitude / turnRadius;
    
    // 4. Apply drift assist
    if (IsDrifting)
    {
        angularVel *= (1f + DriftAssist * 0.5f);
        _velocity = Vector3.Lerp(_velocity, transform.forward * _velocity.magnitude, 
                                  DriftAssist * Time.fixedDeltaTime);
    }
    
    // 5. Apply rotation and position
    transform.Rotate(0, angularVel * Mathf.Rad2Deg * Time.fixedDeltaTime, 0);
    transform.position += _velocity * Time.fixedDeltaTime;
}
```

### InputIntent Abstraction

```csharp
public struct InputIntent
{
    public float Throttle;    // 0-1
    public float Brake;       // 0-1
    public float Steer;       // -1 to 1
    public bool Boost;
    public bool Headlights;   // Flash for challenge
    public bool Pause;
}

public interface IInputProvider
{
    InputIntent GetInput();
}

public class TouchInputProvider : IInputProvider { /* Touch zones */ }
public class TiltInputProvider : IInputProvider { /* Accelerometer */ }
public class GamepadInputProvider : IInputProvider { /* Controller */ }
```

### Default Tuning Parameters

```csharp
public static class DefaultTuning
{
    // Class D (starter cars)
    public static HandlingTuning ClassD = new()
    {
        SteeringSensitivity = 0.6f,
        ThrottleResponse = 0.5f,
        BrakeBalance = 0.55f,
        DriftAssist = 0.7f,      // Very forgiving
        StabilityControl = 0.8f,
        BoostPower = 1.3f
    };
    
    // Class S (top tier)
    public static HandlingTuning ClassS = new()
    {
        SteeringSensitivity = 0.9f,
        ThrottleResponse = 0.95f,
        BrakeBalance = 0.5f,
        DriftAssist = 0.2f,      // Requires skill
        StabilityControl = 0.3f,
        BoostPower = 1.8f
    };
}
```

---

## 8. TOKYO EXTREME RACER–STYLE BATTLE SYSTEM (SPEC)

### Rival Spawning/Visibility

**Spawn Conditions:**

- Player in valid spawn zone
- Zone not on cooldown (10 second minimum between spawns)
- Max 1 active rival at a time
- Spawn probability: 0.2% per tick (≈1 rival per 10 seconds at cruise speed)

**Visibility:**

- Rival appears 200-400m ahead on same highway
- Headlight glow visible at 300m (even before model LOD)
- Rival indicator on minimap when within 500m

### Targeting + Headlight Flash Initiation

```csharp
public class HeadlightFlashSystem
{
    public const float FLASH_RANGE_M = 75f;
    public const float AUTO_ACCEPT_RANGE_M = 30f;
    public const int RESPONSE_WINDOW_TICKS = 180;  // 3 seconds
    
    public bool CanChallenge(EncounterPreLock preLock)
    {
        return preLock.InLockEnvelope
            && preLock.Distance < FLASH_RANGE_M
            && preLock.LOSClear
            && preLock.RelativeSpeed > -10f;  // Not falling too far behind
    }
}
```

### Lock Envelope Rules

| Condition | Threshold | Notes |
|-----------|-----------|-------|
| Distance | < 100m | Either car ahead |
| Same Highway Segment | Required | No cross-highway challenges |
| Player Speed | > 20 m/s (72 km/h) | Must be in motion |
| Line of Sight | Clear | No obstacles between cars |
| Lane Proximity | ≤ 2 lanes apart | Can't challenge across barricade |

### SP Drain Model

**Core Equation:**

```
drain_per_tick = (base + gap_factor + speed_factor) × escalation × (1 / tick_rate)

where:
  base = BASE_DRAIN_PER_SECOND
  gap_factor = gap_meters × GAP_MULTIPLIER
  speed_factor = max(0, leader_speed - follower_speed) × SPEED_MULTIPLIER
  escalation = 1.0 + (battle_duration_seconds × ESCALATION_RATE)
```

**Tunables (Default Values):**

| Parameter | Value | Effect |
|-----------|-------|--------|
| BASE_DRAIN_PER_SECOND | 0.03 | ~33 seconds to empty at standstill |
| GAP_MULTIPLIER | 0.002 | +0.2% drain per 100m gap |
| SPEED_MULTIPLIER | 0.008 | +0.8% drain per 10 m/s speed diff |
| ESCALATION_RATE | 0.0002 | Battles intensify over time |
| COLLISION_PENALTY | 0.05 | Instant drain on wall hit |
| MIN_DRAIN_PER_TICK | 0.0001 | Prevents stalemates |
| MAX_DRAIN_PER_TICK | 0.01 | Prevents instant kills |

### Win/Loss Conditions

| Condition | Winner | Notes |
|-----------|--------|-------|
| Rival SP ≤ 0 | Player | Standard victory |
| Player SP ≤ 0 | Rival | Standard defeat |
| Player crashes (stopped 3s) | Rival | Forfeit |
| Rival crashes (stopped 3s) | Player | Forfeit |
| Gap > 500m for 10s | None | Disengage, no penalty |
| Player enters garage | None | Battle cancelled |

### AI Behaviors During Battle

```csharp
public enum RivalBattleBehavior
{
    Pressure,    // Maintain close gap, mirror player
    Feint,       // Fake lane change to bait reaction
    Yield,       // Let player pass, then draft
    Recovery,    // Fell behind, maximum aggression
    Defensive,   // SP critical, play safe
}

public class RivalBattleAI
{
    public RivalBattleBehavior ChooseBehavior(BattleSession session)
    {
        if (session.RivalSP < 0.25f)
            return RivalBattleBehavior.Defensive;
        if (session.GapMeters > 50f && !session.PlayerIsLeader)
            return RivalBattleBehavior.Recovery;
        if (_random.NextFloat() < _aggression * 0.3f)
            return RivalBattleBehavior.Feint;
        return RivalBattleBehavior.Pressure;
    }
}
```

### Exploit Prevention + Edge Cases

| Exploit | Prevention |
|---------|------------|
| Rubber-banding abuse | SP drain floor prevents zero drain at any gap |
| Wall-riding | Collision penalty drains SP |
| Traffic blocking | Traffic thins 50% during battle |
| Pause abuse | No pause during battle |
| Disconnect/quit | Auto-forfeit after 5 second timeout |
| Speed hacking | Server-authoritative if online; local hash verification |

---

## 9. PROGRESSION & GARAGE LOOP

### Rep/Cash Model

**Earning:**

- Battle victory: `base_rep × tier_multiplier + gap_bonus`
  - Wanderer: 100 rep, 500 cash
  - Boss: 300 rep, 2000 cash
  - Team Leader: 1000 rep, 10000 cash
- Gap bonus: +10% per 10m lead at victory
- First-time defeat bonus: 2× rewards

**Spending:**

- Car unlock: 5000-50000 cash
- Upgrade tier: 1000-5000 cash each
- Cosmetics: 500-2000 cash

### Unlock Gates

```text
Rank 0-10:   D-class cars only, Wanderers only
Rank 11-25:  C-class unlocks, first Bosses appear
Rank 26-50:  B-class unlocks, more Bosses
Rank 51-75:  A-class unlocks, first Team Leaders
Rank 76-99:  S-class unlocks, final Team Leader
Rank 100:    True ending (defeat all Team Leaders)
```

### Rival Tiers

| Tier | SP Pool | Skill | Aggression | Unlock |
|------|---------|-------|------------|--------|
| Wanderer | 0.8 | 0.3-0.5 | 0.3 | Always |
| Boss | 1.2 | 0.6-0.8 | 0.6 | Defeat 5 Wanderers in zone |
| Team Leader | 1.5 | 0.9 | 0.9 | Defeat zone Boss 3× |

### Upgrades

```csharp
public enum UpgradeSlot
{
    Engine,      // +Power
    Tires,       // +Grip
    Suspension,  // +Handling
    Brakes,      // +Stopping
    Turbo,       // +Boost power
    Weight,      // -Mass
}

// Each slot has 3 tiers: Stock → Stage 1 → Stage 2 → Stage 3
```

---

## 10. CONTENT PIPELINE & AUTHORING

### ScriptableObject Patterns

```csharp
[CreateAssetMenu(menuName = "Racing/Rival Definition")]
public class RivalDefinitionSO : ScriptableObject
{
    public string RivalId;
    public string DisplayName;
    public RivalTier Tier;
    public CarSpec Car;
    public SPBarModel SPConfig;
    public float Aggression;
    public string[] SpawnZones;
    public AudioClip TauntClip;
}

[CreateAssetMenu(menuName = "Racing/World Cell")]
public class WorldCellSO : ScriptableObject
{
    public string CellId;
    public Vector2Int GridPosition;
    public GameObject CellPrefab;        // Addressable reference
    public HighwaySegment[] Segments;
    public int MemoryBudgetKB;
}
```

### Addressables Structure

```text
Assets/
├── Addressables/
│   ├── Cars/
│   │   ├── car_s13.prefab
│   │   ├── car_gtr.prefab
│   │   └── ...
│   ├── Cells/
│   │   ├── cell_00_00.prefab
│   │   ├── cell_00_01.prefab
│   │   └── ...
│   ├── Rivals/
│   │   ├── rival_wanderer_001.asset
│   │   ├── rival_boss_karussell.asset
│   │   └── ...
│   └── Audio/
│       ├── engine_inline4.wav
│       └── ...
```

### Designer Workflows

1. **Add New Rival**: Create `RivalDefinitionSO`, assign car, set spawn zones, configure SP
2. **Add New Cell**: Create cell prefab, add `WorldCellSO` metadata, register in `CellManifest`
3. **Tune Handling**: Modify `HandlingTuning` on car prefab, test in `TestScene_Handling`
4. **Add Highway Segment**: Edit `HighwayGraph` asset, define nodes/lanes, link to cells

---

## 11. SAVE/LOAD & GOVERNANCE (FAIL-CLOSED)

### Atomic Operations

| Operation | Atomicity | Validation |
|-----------|-----------|------------|
| Save profile | Full transaction (temp → commit) | Hash verification |
| Battle result | Append-only log | Merkle chain |
| Unlock | Tied to profile save | Condition re-check |
| Purchase | Tied to profile save | Balance check |

### Save File Structure

```text
SaveData/
├── profile.json           # PlayerProfile
├── profile.json.bak       # Previous version
├── profile.hash           # SHA-256 of profile.json
├── battles.ndjson         # Append-only battle log
├── battles.merkle         # Merkle root chain
└── settings.json          # Non-critical preferences
```

### Corruption Recovery

```csharp
public class SaveManager
{
    public PlayerProfile Load()
    {
        try
        {
            var profile = LoadAndValidate("profile.json");
            return profile;
        }
        catch (ValidationException)
        {
            // Try backup
            try
            {
                var backup = LoadAndValidate("profile.json.bak");
                Save(backup);  // Restore backup as primary
                return backup;
            }
            catch
            {
                // Factory reset
                return CreateNewProfile();
            }
        }
    }
    
    private PlayerProfile LoadAndValidate(string path)
    {
        var json = File.ReadAllText(path);
        var hash = ComputeSHA256(json);
        var storedHash = File.ReadAllText(path.Replace(".json", ".hash"));
        
        if (hash != storedHash)
            throw new ValidationException("Hash mismatch");
        
        return JsonUtility.FromJson<PlayerProfile>(json);
    }
}
```

### Battle Replay Seeds

```csharp
public struct BattleReplayData
{
    public int BattleSeed;            // Random seed for determinism
    public int StartTick;
    public InputIntent[] PlayerInputs; // Frame-by-frame inputs
    public float FinalPlayerSP;
    public float FinalRivalSP;
    public string Winner;
    public string ReplayHash;          // SHA-256 of above
}
```

---

## 12. RISKS & MITIGATIONS (TOP 10)

| # | Risk | Impact | Mitigation | Acceptance Criteria |
|---|------|--------|------------|---------------------|
| 1 | Memory pressure from streaming | Crash | Hard 150MB ceiling, aggressive unload | < 1 crash per 1000 sessions |
| 2 | Frame drops during cell load | Poor UX | Async instantiation, max 10 objects/frame | 95th percentile > 28 FPS |
| 3 | SP drain feels unfair | Player frustration | Extensive tuning, difficulty options | Playtest approval 80%+ |
| 4 | AI too predictable | Boring battles | Behavior tree variety, per-rival personality | Playtest "fun" rating 4+/5 |
| 5 | Touch controls unresponsive | Unplayable | Dedicated input layer, low-latency touch | Input lag < 50ms |
| 6 | Save corruption | Progress loss | Fail-closed design, backups, hash validation | 0 reports in production |
| 7 | Physics jitter at low FPS | Poor feel | Fixed timestep, interpolation | Smooth at 30 FPS |
| 8 | Highway graph complexity | Dev time | Visual editor, runtime validation | Graph edits < 5 min each |
| 9 | Content bloat | Download size | Addressables, on-demand loading | Initial download < 100 MB |
| 10 | Progression too fast/slow | Retention | Analytics, server-tunable gates | Week 1 retention > 40% |

---

## 13. IMPLEMENTATION PLAN (FIRST 4 WEEKS)

### Week 1: Core Loop Skeleton

**Deliverables:**

- [ ] `GameModeController` state machine (MENU → FREEROAM → BATTLE stub)
- [ ] `VehicleController` with basic physics (no drift yet)
- [ ] `InputManager` with touch/tilt support
- [ ] Single test cell with highway segment
- [ ] Placeholder cel-shader on one car

**Definition of Done:**

- Player can drive car on test highway with touch controls
- State transitions trigger correctly (verified in console)

### Week 2: Battle System Foundation

**Deliverables:**

- [ ] `SPBarModel` with drain calculation
- [ ] `BattleManager` with full lifecycle
- [ ] `HeadlightFlashSystem` challenge initiation
- [ ] Rival AI stub (follows racing line at fixed speed)
- [ ] Battle HUD (SP bars, gap indicator)

**Definition of Done:**

- Complete battle from challenge → SP drain → victory/defeat
- HUD updates in real-time

### Week 3: World Streaming & Rivals

**Deliverables:**

- [ ] `WorldStreamingManager` with predictive loading
- [ ] `CellManifest` with 4 test cells
- [ ] `RivalManager` + `RivalSpawner`
- [ ] 3 Wanderer rivals with distinct cars
- [ ] Traffic stub (static parked cars)

**Definition of Done:**

- Drive through 4+ cells without load stutter
- Rivals spawn and can be challenged

### Week 4: Polish & Integration

**Deliverables:**

- [ ] Cel-shader on all cars + environment
- [ ] Drift assist tuning pass
- [ ] Boost implementation
- [ ] `ProgressionManager` with rep/cash
- [ ] `SaveManager` with atomic saves
- [ ] Audio: engine loop, battle music

**Definition of Done:**

- Full loop: Start → Drive → Battle → Win → Earn Rep → Save → Quit → Load
- Visual polish at "first playable" level

---

## HANDOFF CONTRACT

### Files/Classes to Create First (In Order)

```text
1. Core/GameModeController.cs
2. Core/TickManager.cs
3. Input/InputIntent.cs
4. Input/InputManager.cs
5. Input/TouchInputProvider.cs
6. Vehicle/VehicleController.cs
7. Vehicle/CarSpec.cs
8. Vehicle/HandlingTuning.cs
9. Battle/SPBarModel.cs
10. Battle/BattleSession.cs
11. Battle/BattleManager.cs
12. Battle/HeadlightFlashSystem.cs
13. Rivals/RivalDefinition.cs
14. Rivals/RivalManager.cs
15. Rivals/RivalSpawner.cs
16. World/WorldCell.cs
17. World/CellManifest.cs
18. World/WorldStreamingManager.cs
19. World/HighwayGraph.cs
20. Progression/PlayerProfile.cs
21. Progression/ProgressionManager.cs
22. Save/SaveManager.cs
23. UI/BattleHUD.cs
24. UI/SPBarUI.cs
```

### Integration Order

1. **Input → Vehicle**: Get car moving with touch
2. **Vehicle → GameMode**: Add state machine, pause handling
3. **SPBarModel → BattleManager → HeadlightFlash**: Battle loop working
4. **RivalDefinition → RivalManager → Battle**: AI opponents
5. **WorldCell → StreamingManager → Highway**: World streaming
6. **PlayerProfile → ProgressionManager → SaveManager**: Persistence
7. **BattleHUD → UIManager**: Visual feedback
8. **CelShader integration**: Polish pass

### Required Test Scenes

| Scene | Purpose | Validation |
|-------|---------|------------|
| `TestScene_Vehicle` | Physics tuning | Car handles well, drifts, boosts |
| `TestScene_Battle` | SP mechanics | Full battle lifecycle works |
| `TestScene_Streaming` | Cell loading | 4 cells load/unload without stutter |
| `TestScene_Rivals` | AI behavior | Rivals spawn, challenge, fight |
| `TestScene_Save` | Persistence | Save → kill → load restores state |
| `TestScene_FullLoop` | Integration | Complete game loop end-to-end |

---

*Architecture Pack v1.0 — Ready for Implementation*
