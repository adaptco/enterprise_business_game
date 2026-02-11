"""
Build Nordschleife Track Model (JSON).

Generates a procedural approximation of the Nürburgring Nordschleife
using a sequence of segments (straight, turn).
Computes points, cumulative distance, and curvature profile.

Output: track_nordschleife.json
"""

import json
import math
import os
import numpy as np

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "track_nordschleife.json")

def generate_track_data():
    """
    Generate points for Nordschleife-like track.
    Total length approx 20.8 km.
    """
    
    # Segment definitions: (type, length_m, curvature_1/m or None)
    # curvature > 0 = Left, < 0 = Right
    # "straight": (length)
    # "turn": (length, curvature)
    
    segments = [
        # Dottinger Hohe (Long straight)
        ("straight", 2000.0),
        
        # Antoniusbuche (Fast Left)
        ("turn", 300.0, 1.0/500.0),
        
        # Tiergarten (Left-Right Chicane)
        ("turn", 100.0, 1.0/100.0),
        ("turn", 100.0, -1.0/100.0),
        ("straight", 100.0),
        
        # Hohenrain (Tight Right-Left)
        ("turn", 150.0, -1.0/60.0),
        ("turn", 150.0, 1.0/60.0),
        
        # Start/Finish (Straight)
        ("straight", 600.0),
        
        # Hatzenbach (Winding section)
        ("turn", 200.0, -1.0/80.0), # R
        ("turn", 150.0, 1.0/70.0),  # L
        ("turn", 150.0, -1.0/70.0), # R
        ("straight", 100.0),
        
        # Hocheichen
        ("turn", 200.0, 1.0/90.0),
        
        # Quiddelbacher Hohe (Fast, crest)
        ("straight", 400.0),
        
        # Flugplatz (Fast Right, double apex)
        ("turn", 300.0, -1.0/150.0),
        ("straight", 300.0),
        
        # Schwedenkreuz (Very Fast Left)
        ("turn", 400.0, 1.0/600.0),
        
        # Aremberg (Tight Right)
        ("straight", 300.0),
        ("turn", 250.0, -1.0/80.0),
        
        # Fuchsprohre (Downhill compression)
        ("straight", 500.0),
        ("turn", 200.0, 1.0/300.0), # Slight left
        ("straight", 200.0),
        ("turn", 200.0, -1.0/300.0), # Slight right
        ("straight", 200.0),
        ("turn", 200.0, 1.0/100.0), # Compression Left
        
        # Adenauer Forst (Technical Chicane)
        ("straight", 200.0),
        ("turn", 100.0, 1.0/50.0), # L
        ("turn", 100.0, -1.0/40.0), # R
        
        # Metzgesfeld
        ("straight", 300.0),
        ("turn", 200.0, 1.0/120.0), # Fast L
        
        # Kallenhard (Tight Right)
        ("turn", 250.0, -1.0/70.0),
        
        # Wehrseifen (Tight Left-Right)
        ("straight", 100.0),
        ("turn", 150.0, 1.0/50.0),
        ("turn", 150.0, -1.0/50.0),
        
        # Ex-Muhle (Right Uphill)
        ("turn", 200.0, -1.0/80.0),
        ("straight", 300.0),
        
        # Bergwerk (Tight Right)
        ("turn", 250.0, -1.0/70.0),
        
        # Kesselchen (Long Fast Uphill Section)
        ("straight", 1000.0),
        ("turn", 500.0, 1.0/600.0), # Gentle L
        ("straight", 500.0),
        
        # Klostertal -> Karussell
        ("turn", 200.0, -1.0/100.0), # R
        ("straight", 200.0),
        ("turn", 150.0, 1.0/60.0),  # Karussell (Banked Left) - Approx
        
        # Hohe Acht (High point)
        ("straight", 300.0),
        ("turn", 200.0, -1.0/90.0), # R
        
        # Wippermann / Eschbach / Brunnchen (Winding)
        ("turn", 200.0, 1.0/80.0), # L
        ("turn", 200.0, -1.0/80.0), # R
        ("straight", 100.0),
        ("turn", 200.0, 1.0/80.0), # L
        ("turn", 200.0, -1.0/70.0), # R (Brunnchen)
        
        # Pflanzgarten (Jumps)
        ("straight", 400.0),
        ("turn", 200.0, -1.0/150.0), # Fast R
        ("straight", 300.0),
        ("turn", 200.0, 1.0/150.0), # Fast L
        
        # Schwalbenschwanz / Kleines Karussell
        ("straight", 400.0),
        ("turn", 200.0, -1.0/100.0), # R
        ("turn", 150.0, 1.0/60.0), # Kleines K (L)
        
        # Galgenkopf (Long Right onto Dottinger output)
        ("turn", 400.0, -1.0/200.0),
        
        # Back to Dottinger Hohe entry
        ("straight", 1000.0)
    ]
    
    points = []
    x, y = 0.0, 0.0
    heading = 0.0
    
    # discretization step
    ds = 5.0 # meters
    
    idx = 0
    total_len = 0.0
    
    for seg in segments:
        seg_type = seg[0]
        length = seg[1]
        
        num_steps = int(length / ds)
        
        if seg_type == "straight":
            curv = 0.0
        else:
            curv = seg[2]
            
        for _ in range(num_steps):
            points.append({
                "idx": idx,
                "x": round(x, 3),
                "y": round(y, 3),
                "z": 0.0, # Flat for v1
                "width": 10.0, # Constant width v1
                "camber": 0.0,
                "curvature": curv,
                "dist": round(total_len, 3)
            })
            
            # Integrate
            x += math.cos(heading) * ds
            y += math.sin(heading) * ds
            heading += curv * ds
            
            total_len += ds
            idx += 1
            
    # Loop closure correction (simple linear distribution of error)
    # The generated track won't perfectly close due to approximation.
    # We'll just leave it open for v1 demo or warp it if needed.
    # For RF driver training, "lap" consistency matters more than perfect geometry.
    
    return {
        "name": "Nordschleife_Procedural_v1",
        "total_length_m": round(total_len, 3),
        "points": points
    }

if __name__ == "__main__":
    track_data = generate_track_data()
    
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(track_data, f, indent=2)
        
    print(f"✅ Generated {OUTPUT_PATH}")
    print(f"   Points: {len(track_data['points'])}")
    print(f"   Length: {track_data['total_length_m']} m")
