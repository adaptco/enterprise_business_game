using Unity.MLAgents;
using Unity.MLAgents.Sensors;
using Unity.MLAgents.Actuators;
using Unity.MLAgents.SideChannels;
using UnityEngine;
using System;

/// <summary>
/// ML-Agents Car Agent with Physics Validation SideChannel integration.
/// 
/// Observation Space (12 floats):
/// 0-2:  velocity_xyz (normalized by 80)
/// 3-5:  angular_velocity_xyz (normalized by 5)
/// 6:    grip_mu (validated, normalized by 2.0)
/// 7:    lat_accel (validated, normalized by 15)
/// 8:    slip_front (validated, [-0.5, 0.5])
/// 9:    slip_rear (validated, [-0.5, 0.5])
/// 10:   throttle_history (prev action)
/// 11:   steer_history (prev action)
/// 
/// Action Space (2 continuous):
/// 0: throttle [-1, 1] (negative = brake)
/// 1: steer [-1, 1]
/// </summary>
public class CarAgent : Agent
{
    [Header("Physics Components")]
    public Rigidbody rb;
    public WheelCollider[] wheels = new WheelCollider[4]; // FL, FR, RL, RR
    
    [Header("Vehicle Parameters")]
    public float maxMotorForce = 2000f;
    public float maxBrakeForce = 3000f;
    public float maxSteerAngle = 30f;
    
    [Header("Validated Physics State (from Python)")]
    [SerializeField] private float validatedGripMu = 1.2f;
    [SerializeField] private float validatedLatAccel = 0f;
    [SerializeField] private float validatedSlipFront = 0f;
    [SerializeField] private float validatedSlipRear = 0f;
    
    [Header("Training")]
    public Transform[] trackWaypoints;
    public int currentWaypoint = 0;
    
    // Action history for observation
    private float[] prevActions = new float[2];
    
    // SideChannel for physics validation
    private PhysicsValidationSideChannel physicsChannel;
    
    public override void Initialize()
    {
        // Register physics validation side channel
        physicsChannel = new PhysicsValidationSideChannel();
        SideChannelManager.RegisterSideChannel(physicsChannel);
        
        // Subscribe to validated physics updates
        physicsChannel.OnValidatedPhysicsReceived += OnValidatedPhysicsReceived;
    }
    
    public override void OnEpisodeBegin()
    {
        // Reset car position and physics
        transform.localPosition = new Vector3(0f, 0.5f, 0f);
        transform.localRotation = Quaternion.identity;
        rb.velocity = Vector3.zero;
        rb.angularVelocity = Vector3.zero;
        
        // Reset state
        currentWaypoint = 0;
        prevActions[0] = 0f;
        prevActions[1] = 0f;
        validatedGripMu = 1.2f;
        validatedLatAccel = 0f;
        validatedSlipFront = 0f;
        validatedSlipRear = 0f;
    }
    
    public override void CollectObservations(VectorSensor sensor)
    {
        // Raw Unity physics (0-5)
        sensor.AddObservation(rb.velocity / 80f);           // 0-2: normalized velocity
        sensor.AddObservation(rb.angularVelocity / 5f);     // 3-5: normalized angular velocity
        
        // Python-validated physics (6-9) - guaranteed physics-legal
        sensor.AddObservation(validatedGripMu / 2f);        // 6: normalized grip
        sensor.AddObservation(validatedLatAccel / 15f);     // 7: normalized lateral accel
        sensor.AddObservation(validatedSlipFront);          // 8: front slip angle
        sensor.AddObservation(validatedSlipRear);           // 9: rear slip angle
        
        // Action history for temporal coherence (10-11)
        sensor.AddObservation(prevActions[0]);              // 10: prev throttle
        sensor.AddObservation(prevActions[1]);              // 11: prev steer
        
        // Total: 12 continuous observations
        
        // Send raw physics to Python for validation
        SendPhysicsForValidation();
    }
    
    public override void OnActionReceived(ActionBuffers actions)
    {
        // Extract continuous actions
        float throttle = Mathf.Clamp(actions.ContinuousActions[0], -1f, 1f);
        float steer = Mathf.Clamp(actions.ContinuousActions[1], -1f, 1f);
        
        // Store for next observation
        prevActions[0] = throttle;
        prevActions[1] = steer;
        
        // Apply control
        ApplyControl(throttle, steer);
        
        // Compute and add reward
        float reward = ComputeReward();
        AddReward(reward);
        
        // Check termination conditions
        CheckTermination();
    }
    
    public override void Heuristic(in ActionBuffers actionsOut)
    {
        // Manual control for testing
        var continuousActions = actionsOut.ContinuousActions;
        continuousActions[0] = Input.GetAxis("Vertical");   // W/S
        continuousActions[1] = Input.GetAxis("Horizontal"); // A/D
    }
    
    private void ApplyControl(float throttle, float steer)
    {
        // Rear wheel drive
        float motorTorque = throttle > 0 ? throttle * maxMotorForce : 0f;
        float brakeTorque = throttle < 0 ? -throttle * maxBrakeForce : 0f;
        
        wheels[2].motorTorque = motorTorque;  // RL
        wheels[3].motorTorque = motorTorque;  // RR
        
        // Apply brakes to all wheels
        foreach (var wheel in wheels)
        {
            wheel.brakeTorque = brakeTorque;
        }
        
        // Front wheel steering
        float steerAngle = steer * maxSteerAngle;
        wheels[0].steerAngle = steerAngle;    // FL
        wheels[1].steerAngle = steerAngle;    // FR
    }
    
    private float ComputeReward()
    {
        // Progress reward: forward velocity toward waypoint
        float progressReward = rb.velocity.magnitude / 80f;
        
        // Stability reward: penalize excessive slip
        float stabilityReward = 1f - Mathf.Abs(validatedSlipRear);
        
        // Grip reward: reward maintaining grip
        float gripReward = validatedGripMu / 2f;
        
        // Waypoint progress bonus
        float waypointBonus = 0f;
        if (trackWaypoints != null && trackWaypoints.Length > 0)
        {
            float distToWaypoint = Vector3.Distance(
                transform.position, 
                trackWaypoints[currentWaypoint].position
            );
            
            if (distToWaypoint < 5f)
            {
                waypointBonus = 1f;
                currentWaypoint = (currentWaypoint + 1) % trackWaypoints.Length;
            }
        }
        
        // Combined reward with step penalty
        return progressReward * stabilityReward * gripReward + waypointBonus - 0.001f;
    }
    
    private void CheckTermination()
    {
        // Off track detection
        if (Mathf.Abs(transform.position.x) > 20f || Mathf.Abs(transform.position.z) > 200f)
        {
            AddReward(-1f);
            EndEpisode();
        }
        
        // Upside down detection
        if (Vector3.Dot(transform.up, Vector3.up) < 0.5f)
        {
            AddReward(-1f);
            EndEpisode();
        }
        
        // Stalled detection
        if (rb.velocity.magnitude < 0.1f && StepCount > 100)
        {
            AddReward(-0.5f);
            EndEpisode();
        }
    }
    
    private void SendPhysicsForValidation()
    {
        // Compute slip angles (simplified)
        Vector3 localVel = transform.InverseTransformDirection(rb.velocity);
        float slipFront = Mathf.Atan2(localVel.x, Mathf.Max(localVel.z, 0.1f));
        float slipRear = slipFront * 0.8f; // Simplified rear slip
        
        // Compute lateral acceleration
        float latAccel = localVel.x * rb.angularVelocity.y;
        
        // Estimate grip (simplified)
        float baseGrip = 1.2f;
        float slipPenalty = Mathf.Max(Mathf.Abs(slipFront), Mathf.Abs(slipRear)) * 0.5f;
        float grip = Mathf.Max(0.3f, baseGrip - slipPenalty);
        
        // Send to Python via SideChannel
        physicsChannel.SendPhysicsData(
            Time.time,
            rb.velocity.magnitude,
            rb.angularVelocity.y,
            wheels[0].steerAngle * Mathf.Deg2Rad,
            grip,
            slipFront,
            slipRear,
            latAccel,
            0f // cornering stiffness placeholder
        );
    }
    
    private void OnValidatedPhysicsReceived(float[] validatedData)
    {
        if (validatedData.Length >= 4)
        {
            validatedGripMu = validatedData[0];
            validatedLatAccel = validatedData[1];
            validatedSlipFront = validatedData[2];
            validatedSlipRear = validatedData[3];
        }
    }
    
    private void OnDestroy()
    {
        // Cleanup side channel
        if (physicsChannel != null)
        {
            physicsChannel.OnValidatedPhysicsReceived -= OnValidatedPhysicsReceived;
            SideChannelManager.UnregisterSideChannel(physicsChannel);
        }
    }
}
