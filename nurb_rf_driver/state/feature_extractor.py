"""
Feature extraction for RF driver state vector v1.
Computes canonical 10-feature vector in stable order.
"""

import json
import os
from typing import Dict, Any, List, Tuple
from dataclasses import asdict


# Load feature config for stable ordering
_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "feature_config.v1.json")
with open(_CONFIG_PATH, 'r') as f:
    FEATURE_CONFIG = json.load(f)

# Precompute feature ordering
FEATURE_ORDER = [feat["name"] for feat in sorted(FEATURE_CONFIG["features"], key=lambda x: x["index"])]
TARGET_ORDER = [tgt["name"] for tgt in FEATURE_CONFIG["targets"]]


class FeatureExtractor:
    """
    Extract v1 feature vector from vehicle state.
    Maintains canonical ordering per feature_config.v1.json.
    """
    
    def __init__(self):
        self.feature_config = FEATURE_CONFIG
        self.feature_order = FEATURE_ORDER
        self.target_order = TARGET_ORDER
        self.num_features = len(self.feature_order)
    
    def extract_features(self, vehicle_state) -> List[float]:
        """
        Extract features from vehicle state in canonical order.
        
        Args:
            vehicle_state: VehicleState dataclass instance
        
        Returns:
            List of 10 floats in canonical order
        """
        state_dict = asdict(vehicle_state) if hasattr(vehicle_state, '__dataclass_fields__') else vehicle_state
        
        features = []
        for feat_name in self.feature_order:
            value = state_dict.get(feat_name, 0.0)
            features.append(float(value))
        
        assert len(features) == self.num_features, \
            f"Expected {self.num_features} features, got {len(features)}"
        
        return features
    
    def extract_targets(self, vehicle_state) -> Dict[str, float]:
        """
        Extract control targets from vehicle state.
        
        Args:
            vehicle_state: VehicleState dataclass instance
        
        Returns:
            Dictionary with steering_command, throttle_command, brake_command
        """
        state_dict = asdict(vehicle_state) if hasattr(vehicle_state, '__dataclass_fields__') else vehicle_state
        
        # Map internal state names to target names
        targets = {
            "steering_command": float(state_dict.get("steering_angle_norm", 0.0)),
            "throttle_command": float(state_dict.get("throttle_norm", 0.0)),
            "brake_command": float(state_dict.get("brake_norm", 0.0))
        }
        
        return targets
    
    def features_to_dict(self, features: List[float]) -> Dict[str, float]:
        """
        Convert feature list to named dictionary.
        
        Args:
            features: List of feature values in canonical order
        
        Returns:
            Dictionary mapping feature names to values
        """
        assert len(features) == self.num_features, \
            f"Expected {self.num_features} features, got {len(features)}"
        
        return {name: features[i] for i, name in enumerate(self.feature_order)}
    
    def validate_feature_keys(self, feature_dict: Dict[str, Any]) -> bool:
        """
        Validate that feature dictionary has exactly the expected keys.
        
        Args:
            feature_dict: Dictionary of features
        
        Returns:
            True if valid, False otherwise
        """
        expected = set(self.feature_order)
        actual = set(feature_dict.keys())
        
        if expected != actual:
            missing = expected - actual
            extra = actual - expected
            if missing:
                print(f"❌ Missing features: {missing}")
            if extra:
                print(f"❌ Extra features: {extra}")
            return False
        
        return True
    
    def normalize_features(self, features: List[float]) -> List[float]:
        """
        Normalize features according to feature_config.v1.json specifications.
        
        Args:
            features: Raw feature values
        
        Returns:
            Normalized feature values in [0, 1] or [-1, 1] depending on spec
        """
        normalized = []
        
        for i, value in enumerate(features):
            feat_info = self.feature_config["features"][i]
            norm_method = feat_info.get("normalization", "none")
            max_val = feat_info.get("max_value", 1.0)
            
            if norm_method == "already_normalized":
                normalized.append(value)
            elif norm_method == "divide_by_max":
                normalized.append(value / max_val)
            elif norm_method == "divide_by_pi":
                normalized.append(value / 3.14159)
            else:
                normalized.append(value)
        
        return normalized
    
    def get_feature_names(self) -> List[str]:
        """Get canonical feature names in order."""
        return self.feature_order.copy()
    
    def get_target_names(self) -> List[str]:
        """Get canonical target names in order."""
        return self.target_order.copy()
    
    def get_feature_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        Get metadata for all features.
        
        Returns:
            Dictionary mapping feature names to their metadata
        """
        metadata = {}
        for feat in self.feature_config["features"]:
            metadata[feat["name"]] = {
                "index": feat["index"],
                "type": feat["type"],
                "unit": feat["unit"],
                "description": feat["description"],
                "normalization": feat.get("normalization"),
                "max_value": feat.get("max_value")
            }
        return metadata


# Singleton instance for consistent extraction
_extractor = FeatureExtractor()


def extract_features(vehicle_state) -> List[float]:
    """
    Convenience function for feature extraction.
    Uses singleton extractor to ensure consistency.
    """
    return _extractor.extract_features(vehicle_state)


def extract_targets(vehicle_state) -> Dict[str, float]:
    """
    Convenience function for target extraction.
    Uses singleton extractor to ensure consistency.
    """
    return _extractor.extract_targets(vehicle_state)


def get_feature_names() -> List[str]:
    """Get canonical feature names."""
    return _extractor.get_feature_names()


def validate_feature_dict(feature_dict: Dict[str, Any]) -> bool:
    """Validate feature dictionary has correct keys."""
    return _extractor.validate_feature_keys(feature_dict)
