using Unity.MLAgents.SideChannels;
using System;

/// <summary>
/// SideChannel for physics validation between Unity and Python.
/// Matches UUID: 12345678-9abc-def0-1234-56789abcdef0
/// </summary>
public class PhysicsValidationSideChannel : SideChannel
{
    // Event fired when Python returns validated physics
    public event Action<float[]> OnValidatedPhysicsReceived;
    
    public PhysicsValidationSideChannel()
    {
        // Must match Python's CHANNEL_ID
        ChannelId = new Guid("12345678-9abc-def0-1234-56789abcdef0");
    }
    
    protected override void OnMessageReceived(IncomingMessage msg)
    {
        // Read validated tensor from Python (4 floats: grip, lat_accel, slip_front, slip_rear)
        var validatedData = new float[4];
        for (int i = 0; i < 4; i++)
        {
            validatedData[i] = msg.ReadFloat32();
        }
        
        // Fire event to update agent
        OnValidatedPhysicsReceived?.Invoke(validatedData);
    }
    
    /// <summary>
    /// Send raw physics data to Python for validation.
    /// </summary>
    public void SendPhysicsData(
        float timestamp,
        float velocity,
        float yawRate,
        float steeringAngle,
        float gripMu,
        float slipFront,
        float slipRear,
        float latAccel,
        float corneringStiffness)
    {
        using (var msg = new OutgoingMessage())
        {
            // Write 16 floats to match Python expectation
            msg.WriteFloat32(timestamp);      // 0
            msg.WriteFloat32(velocity);       // 1
            msg.WriteFloat32(yawRate);        // 2
            msg.WriteFloat32(steeringAngle);  // 3
            msg.WriteFloat32(gripMu);         // 4
            
            // Placeholders for indices 5-11
            for (int i = 0; i < 7; i++)
            {
                msg.WriteFloat32(0f);
            }
            
            // RCVD dynamics at indices 12-15
            msg.WriteFloat32(slipFront);            // 12
            msg.WriteFloat32(slipRear);             // 13
            msg.WriteFloat32(latAccel);             // 14
            msg.WriteFloat32(corneringStiffness);   // 15
            
            QueueMessageToSend(msg);
        }
    }
}
