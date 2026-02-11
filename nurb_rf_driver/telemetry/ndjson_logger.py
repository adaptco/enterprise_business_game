"""
NDJSON telemetry logger with deterministic key ordering.
Writes training samples in stable format for RF driver.
"""

import json
import os
from typing import Dict, Any, Optional, TextIO
from datetime import datetime, timezone


class NDJSONLogger:
    """
    Newline-delimited JSON logger for training samples.
    Ensures stable key ordering per training_sample.v1.schema.json.
    """
    
    # Canonical key order for top-level fields
    TOP_LEVEL_ORDER = ["tick", "timestamp_ms", "lap_id", "valid", "features", "targets", "meta"]
    
    # Canonical feature key order (matches feature_config.v1.json)
    FEATURE_ORDER = [
        "speed_mps",
        "yaw_rate_rps",
        "steering_angle_norm",
        "track_progress",
        "dist_to_centerline_m",
        "heading_error_rad",
        "curvature_now",
        "curvature_ahead_10m",
        "curvature_ahead_30m",
        "curvature_ahead_60m"
    ]
    
    # Canonical target key order
    TARGET_ORDER = ["steering_command", "throttle_command", "brake_command"]
    
    # Canonical meta key order
    META_ORDER = ["coord_int", "seed_u64", "state_hash", "chain_hash"]
    
    def __init__(self, output_path: str, lap_id: str):
        """
        Initialize NDJSON logger.
        
        Args:
            output_path: Path to output .ndjson file
            lap_id: Unique lap identifier
        """
        self.output_path = output_path
        self.lap_id = lap_id
        self.file_handle: Optional[TextIO] = None
        self.samples_written = 0
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    def open(self):
        """Open file handle for writing."""
        self.file_handle = open(self.output_path, 'w', encoding='utf-8')
        print(f"📝 Opened NDJSON log: {self.output_path}")
    
    def close(self):
        """Close file handle and flush."""
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None
            print(f"✅ Closed NDJSON log: {self.output_path} ({self.samples_written} samples)")
    
    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def _ordered_dict(self, data: Dict[str, Any], order: list) -> Dict[str, Any]:
        """
        Return dictionary with keys in specified order.
        Skips keys not in data.
        """
        ordered = {}
        for key in order:
            if key in data:
                ordered[key] = data[key]
        return ordered
    
    def log_sample(
        self,
        tick: int,
        timestamp_ms: int,
        features: Dict[str, float],
        targets: Dict[str, float],
        valid: bool = True,
        meta: Optional[Dict[str, Any]] = None
    ):
        """
        Log a single training sample.
        
        Args:
            tick: Simulation tick number
            timestamp_ms: Elapsed time in milliseconds
            features: Feature dictionary (will be ordered canonically)
            targets: Target dictionary (will be ordered canonically)
            valid: Whether sample is valid for training
            meta: Optional metadata (coord_int, seed_u64, state_hash, chain_hash)
        """
        if not self.file_handle:
            raise RuntimeError("Logger not opened. Use context manager or call open() first.")
        
        # Build sample with canonical ordering
        sample = {}
        
        # Top-level fields in order
        sample["tick"] = tick
        sample["timestamp_ms"] = timestamp_ms
        sample["lap_id"] = self.lap_id
        sample["valid"] = valid
        
        # Features in canonical order
        sample["features"] = self._ordered_dict(features, self.FEATURE_ORDER)
        
        # Targets in canonical order
        sample["targets"] = self._ordered_dict(targets, self.TARGET_ORDER)
        
        # Optional meta in canonical order
        if meta:
            sample["meta"] = self._ordered_dict(meta, self.META_ORDER)
        
        # Ensure top-level ordering
        sample_ordered = self._ordered_dict(sample, self.TOP_LEVEL_ORDER)
        
        # Write as single JSON line (sort_keys=False to preserve manual order)
        json_line = json.dumps(sample_ordered, sort_keys=False, separators=(',', ':'))
        self.file_handle.write(json_line + '\n')
        self.file_handle.flush()  # Ensure immediate write
        
        self.samples_written += 1
    
    def log_from_sim_state(
        self,
        tick: int,
        timestamp_ms: int,
        vehicle_state,
        metadata: Dict[str, Any],
        feature_extractor,
        valid: bool = True
    ):
        """
        Convenience method to log from simulation state.
        
        Args:
            tick: Current tick
            timestamp_ms: Timestamp in milliseconds
            vehicle_state: VehicleState object
            metadata: Metadata dict from sim_env.step()
            feature_extractor: FeatureExtractor instance
            valid: Whether sample is valid
        """
        # Extract features and targets
        feature_list = feature_extractor.extract_features(vehicle_state)
        feature_dict = feature_extractor.features_to_dict(feature_list)
        target_dict = feature_extractor.extract_targets(vehicle_state)
        
        # Build meta from simulation metadata
        meta = {
            "coord_int": list(metadata.get("coord_int", [0, 0, 0])),
            "seed_u64": metadata.get("seed_u64", 0),
            "state_hash": metadata.get("state_hash", "0" * 64),
            "chain_hash": metadata.get("chain_hash", "0" * 64)
        }
        
        # Log sample
        self.log_sample(
            tick=tick,
            timestamp_ms=timestamp_ms,
            features=feature_dict,
            targets=target_dict,
            valid=valid,
            meta=meta
        )


def load_ndjson(filepath: str) -> list:
    """
    Load NDJSON file and return list of samples.
    
    Args:
        filepath: Path to .ndjson file
    
    Returns:
        List of sample dictionaries
    """
    samples = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                sample = json.loads(line)
                samples.append(sample)
            except json.JSONDecodeError as e:
                print(f"⚠️  Skipping malformed JSON at line {line_num}: {e}")
    
    return samples


def verify_ndjson_determinism(filepath1: str, filepath2: str) -> bool:
    """
    Verify two NDJSON files are byte-for-byte identical.
    
    Args:
        filepath1: First file path
        filepath2: Second file path
    
    Returns:
        True if files are identical, False otherwise
    """
    import hashlib
    
    def file_hash(path: str) -> str:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                h.update(chunk)
        return h.hexdigest()
    
    hash1 = file_hash(filepath1)
    hash2 = file_hash(filepath2)
    
    if hash1 == hash2:
        print(f"✅ Files are identical: {hash1}")
        return True
    else:
        print(f"❌ Files differ:")
        print(f"   File 1: {hash1}")
        print(f"   File 2: {hash2}")
        return False
