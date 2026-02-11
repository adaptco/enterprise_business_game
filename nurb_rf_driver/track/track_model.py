"""
Track Model and Spline Interpolation.
Provides mathematical representation of the track centerline, width, and curvature.
"""

import json
import math
import bisect
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional

@dataclass
class TrackPoint:
    """A single point definition on the track centerline."""
    idx: int
    x_m: float
    y_m: float
    z_m: float
    width_m: float
    camber_rad: float = 0.0

@dataclass
class SplineSegment:
    """Cubic spline coefficients for a segment between two track points."""
    x0: float
    dx: float  # x(s) = a + b*s + c*s^2 + d*s^3
    a_x: float
    b_x: float
    c_x: float
    d_x: float
    
    y0: float
    dy: float
    a_y: float
    b_y: float
    c_y: float
    d_y: float
    
    length_m: float
    cumulative_dist_m: float

class TrackModel:
    """
    Represent the track using cubic splines for smooth curvature.
    """
    
    def __init__(self, track_json_path: str):
        with open(track_json_path, 'r') as f:
            data = json.load(f)
            
        self.name = data.get("name", "Unknown")
        self.total_length_m = data.get("total_length_m", 0.0)
        
        # Load raw points
        self.raw_points: List[TrackPoint] = []
        for p in data.get("points", []):
            self.raw_points.append(TrackPoint(
                idx=p["idx"],
                x_m=p["x"],
                y_m=p["y"],
                z_m=p.get("z", 0.0),
                width_m=p.get("width", 10.0),
                camber_rad=p.get("camber", 0.0)
            ))
            
        # Build splines (placeholder: simple linear segments for now, TODO: Cubic)
        # For v1, we will use piecewise linear with smoothed curvature lookups
        # or implement simple cubic Hermite splines if needed.
        # For simplicity in this step, we'll store points and implement
        # a query method that linearly interpolates.
        
        # Precompute cumulative distance
        self.cumulative_dist = [0.0]
        for i in range(1, len(self.raw_points)):
            p0 = self.raw_points[i-1]
            p1 = self.raw_points[i]
            dist = math.sqrt((p1.x_m - p0.x_m)**2 + (p1.y_m - p0.y_m)**2)
            self.cumulative_dist.append(self.cumulative_dist[-1] + dist)
            
        self.total_length_m = self.cumulative_dist[-1]

    def get_state_at_distance(self, dist_m: float) -> Dict[str, float]:
        """
        Get track state (x, y, heading, curvature, width) at distance s.
        Handles wrapping for closed tracks.
        """
        dist_m = dist_m % self.total_length_m
        
        # Find segment
        idx = bisect.bisect_right(self.cumulative_dist, dist_m) - 1
        idx = max(0, min(idx, len(self.raw_points) - 2))
        
        p0 = self.raw_points[idx]
        p1 = self.raw_points[idx + 1]
        
        s0 = self.cumulative_dist[idx]
        s1 = self.cumulative_dist[idx + 1]
        segment_len = s1 - s0
        
        if segment_len < 1e-6:
            alpha = 0.0
        else:
            alpha = (dist_m - s0) / segment_len
            
        # Linear interp for pos
        x = p0.x_m + alpha * (p1.x_m - p0.x_m)
        y = p0.y_m + alpha * (p1.y_m - p0.y_m)
        width = p0.width_m + alpha * (p1.width_m - p0.width_m)
        
        # Heading (tangent)
        heading = math.atan2(p1.y_m - p0.y_m, p1.x_m - p0.x_m)
        
        # Curvature (requires 3 points, simplified here)
        # For true curvature, we need the spline derivatives.
        # Placeholder: 0.0 for linear segments
        curvature = 0.0 
        
        # Better curvature estimation: Circle through prev, curr, next
        if idx > 0 and idx < len(self.raw_points) - 2:
            pp = self.raw_points[idx-1]
            # Use 3 points: pp, p0, p1 to estimate curvature at p0?
            # This is rough. For v2 we want cubic splines.
            pass

        return {
            "x": x,
            "y": y,
            "heading": heading,
            "curvature": curvature,
            "width": width,
            "idx": idx,
            "alpha": alpha
        }

    def curvature_at(self, dist_m: float) -> float:
        """Get curvature at specific distance."""
        # For now, return 0 or look up precomputed curvature
        # Implementation to be refined with build_track.py pre-calculation
        return self.get_state_at_distance(dist_m)["curvature"]
