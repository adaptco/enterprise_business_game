"""
Validation tests for Sim Env Contract v1.
KPIs:
1. Determinism: 100% hash match on replay
2. Feature Integrity: Canonical extraction order
3. Logging: NDJSON stable serialization
"""

import unittest
import os
import shutil
import json
import sys

# Ensure parent path is in sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from env.sim_env import SimEnv
from state.feature_extractor import FeatureExtractor
from telemetry.ndjson_logger import NDJSONLogger, load_ndjson


class TestSimEnvValidation(unittest.TestCase):
    
    def setUp(self):
        self.output_dir = os.path.join(os.path.dirname(__file__), "test_data")
        os.makedirs(self.output_dir, exist_ok=True)
    
    def tearDown(self):
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

    def test_kpi_1_determinism(self):
        """KPI 1: Verify 100% Determinism on Replay."""
        # Run 1
        env1 = SimEnv(seed=42, run_id="test_run", root_identity="Han")
        env1.reset()
        hashes1 = []
        for _ in range(20):
            _, meta = env1.step(0.1, 0.5, 0.0)
            hashes1.append(meta['chain_hash'])
            
        # Run 2
        env2 = SimEnv(seed=42, run_id="test_run", root_identity="Han")
        env2.reset()
        hashes2 = []
        for _ in range(20):
            _, meta = env2.step(0.1, 0.5, 0.0)
            hashes2.append(meta['chain_hash'])
            
        self.assertEqual(hashes1, hashes2, "Determinism Check Failed: Hash chains do not match.")
        print("\n✅ KPI 1 Passed: Determinism verified (20/20 ticks identical)")

    def test_kpi_2_feature_integrity(self):
        """KPI 2: Verify Canonical Feature Extraction."""
        env = SimEnv(seed=100)
        state = env.reset()
        extractor = FeatureExtractor()
        
        features = extractor.extract_features(state)
        feature_names = extractor.get_feature_names()
        
        # Check count
        self.assertEqual(len(features), 10, "Feature Count Mismatch")
        
        # Check order (sampling a few expected names in order)
        expected_start = ["speed_mps", "yaw_rate_rps", "steering_angle_norm"]
        self.assertEqual(feature_names[:3], expected_start, "Canonical Ordering Violation")
        
        print("\n✅ KPI 2 Passed: Feature integrity verified (10 features, canonical order)")

    def test_kpi_3_logging_stability(self):
        """KPI 3: Verify NDJSON Logging Stability."""
        log_path = os.path.join(self.output_dir, "test.ndjson")
        env = SimEnv(seed=123)
        state = env.reset()
        extractor = FeatureExtractor()
        _, meta = env.step(0.0, 0.0, 0.0)
        
        # Write log
        with NDJSONLogger(log_path, lap_id="test_lap") as logger:
            logger.log_from_sim_state(1, 20, state, meta, extractor)
            
        # Read back purely as text to check key ordering string
        with open(log_path, 'r') as f:
            line = f.read().strip()
            
        # Expected substrings in order
        self.assertIn('"tick":', line)
        self.assertIn('"features":', line)
        self.assertIn('"targets":', line)
        
        # Verify strict key occurrence order in string
        tick_idx = line.find('"tick"')
        feat_idx = line.find('"features"')
        targ_idx = line.find('"targets"')
        meta_idx = line.find('"meta"')
        
        self.assertTrue(tick_idx < feat_idx < targ_idx < meta_idx, "Log Key Ordering Violation")
        print("\n✅ KPI 3 Passed: NDJSON Logging Stability verified")

if __name__ == '__main__':
    unittest.main()
